import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchStockKline, fetchStockHLAnalysis, fetchStockAllHistoricLows } from '../services/api';

function StockChart() {
  
  const [stockId, setStockId] = useState('000002.SZ');
  const [klineData, setKlineData] = useState(null);
  const [hlData, setHlData] = useState(null);
  const [allHistoricLows, setAllHistoricLows] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pointDetails, setPointDetails] = useState(new Map());
  const chartRef = useRef(null);
  
  // 强制图表重新渲染的触发器
  const [chartKey, setChartKey] = useState(0);

  // 获取K线数据
  const fetchKlineData = async () => {
    try {
      console.log('Fetching K-line data for:', stockId);
      const data = await fetchStockKline(stockId, 'daily');
      console.log('K-line data received:', data);
      setKlineData(data);
    } catch (err) {
      console.error('K-line data fetch failed:', err);
      setError(`获取K线数据失败: ${err.message}`);
    }
  };

  // 获取HL分析数据
  const fetchHLData = async () => {
    try {
      console.log('Fetching HL analysis data for:', stockId);
      const data = await fetchStockHLAnalysis(stockId);
      console.log('HL analysis data received:', data);
      setHlData(data);
      
      // 更新点位详细信息
      updatePointDetails(data);
    } catch (err) {
      console.error('获取HL分析数据失败:', err);
      setError(`获取HL分析数据失败: ${err.message}`);
    }
  };

  // 获取所有历史低点数据
  const fetchAllHistoricLows = async () => {
    try {
      console.log('Fetching all historic lows for:', stockId);
      const data = await fetchStockAllHistoricLows(stockId);
      console.log('All historic lows data received:', data);
      setAllHistoricLows(data);
    } catch (err) {
      console.error('获取所有历史低点失败:', err);
      // 不设置错误，因为这不是必需的
    }
  };

  // 更新点位详细信息
  const updatePointDetails = (hlData) => {
    const newPointDetails = new Map();
    
    if (hlData && hlData.results) {
      const results = hlData.results || [];
      
      // 处理所有投资记录
      results.forEach(result => {
        const investmentInfo = result.investment_info || {};
        const settlementInfo = result.settlement_info || {};
        
        // 买入点
        if (investmentInfo.start_date && investmentInfo.purchase_price) {
          const pointKey = `buy_${investmentInfo.start_date}`;
          newPointDetails.set(pointKey, {
            type: 'buy',
            date: investmentInfo.start_date,
            price: investmentInfo.purchase_price,
            target_win: investmentInfo.target_win,
            target_loss: investmentInfo.target_loss,
            stock_name: hlData.stock_info?.name || 'Unknown',
            // 添加之前出现的历史低价点信息
            previous_low_points: investmentInfo.previous_low_points || []
          });
        }
        
        // 卖出点（如果有结算信息）
        if (settlementInfo.exit_date && settlementInfo.exit_price) {
          const pointKey = `sell_${settlementInfo.exit_date}`;
          newPointDetails.set(pointKey, {
            type: result.status === 'win' ? 'sell_win' : 'sell_loss',
            date: settlementInfo.exit_date,
            price: settlementInfo.exit_price,
            stock_name: hlData.stock_info?.name || 'Unknown'
          });
        }
        
        // 历史低点参考（移除紫色参考点，改为低点标记线）
        if (investmentInfo.historic_low_ref?.date && investmentInfo.historic_low_ref?.lowest_price) {
          const pointKey = `low_${investmentInfo.historic_low_ref.date}`;
          newPointDetails.set(pointKey, {
            type: 'low_point',
            date: investmentInfo.historic_low_ref.date,
            price: investmentInfo.historic_low_ref.lowest_price,
            stock_name: hlData.stock_info?.name || 'Unknown'
          });
        }
      });
    }
    
    setPointDetails(newPointDetails);
  };

    // 生成历史低点标记线数据
  const generateLowPointMarkLines = () => {
    console.log('generateLowPointMarkLines called');
    console.log('allHistoricLows:', allHistoricLows);
    console.log('hlData:', hlData);
    
    // 优先使用所有计算出的历史低点数据
    console.log('Checking allHistoricLows condition:');
    console.log('allHistoricLows exists:', !!allHistoricLows);
    console.log('allHistoricLows.all_historic_lows exists:', !!(allHistoricLows && allHistoricLows.all_historic_lows));
    
    if (allHistoricLows && allHistoricLows.all_historic_lows) {
      console.log('✅ Using allHistoricLows data, count:', allHistoricLows.all_historic_lows.length);
      const lowPointLines = [];
      allHistoricLows.all_historic_lows.forEach(lowPoint => {
        lowPointLines.push({
          yAxis: lowPoint.lowest_price,
          name: `历史低点: ${lowPoint.lowest_price}`,
          lineStyle: {
            color: '#666666', // 灰色
            width: 1,
            type: 'dashed'  // 虚线
          }
        });
      });
      console.log('Generated low point lines:', lowPointLines);
      return lowPointLines;
    } else {
      console.log('❌ allHistoricLows condition failed');
    }
    
    // 如果没有所有历史低点数据，则从HL分析数据中提取
    console.log('Checking hlData condition:');
    console.log('hlData exists:', !!hlData);
    console.log('hlData.results exists:', !!(hlData && hlData.results));
    
    if (hlData && hlData.results) {
      console.log('✅ Using HL data, results count:', hlData.results.length);
      const results = hlData.results || [];
      const lowPointLines = [];
      
      // 从所有投资记录中提取历史低点
      results.forEach(result => {
        const investmentInfo = result.investment_info || {};
        if (investmentInfo.historic_low_ref?.date && investmentInfo.historic_low_ref?.lowest_price) {
          lowPointLines.push({
            yAxis: investmentInfo.historic_low_ref.lowest_price,
            name: `历史低点: ${investmentInfo.historic_low_ref.lowest_price}`,
            lineStyle: {
              color: '#333333', // 灰色
              width: 1,
              type: 'dashed'  // 虚线
            }
          });
        }
      });
      
      // 去重
      const uniquePrices = [...new Set(lowPointLines.map(line => line.yAxis))];
      const uniqueLowPointLines = uniquePrices.map(price => ({
        yAxis: price,
        name: `历史低点: ${price}`,
        lineStyle: {
          color: '#666666',
          width: 1,
          type: 'dashed'
        }
      }));
      
      console.log('Generated unique low point lines:', uniqueLowPointLines);
      return uniqueLowPointLines;
    } else {
      console.log('❌ hlData condition failed');
    }
    
    console.log('No data available, returning empty array');
    return [];
  };

  // 加载数据
  const handleLoadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('Starting data loading...');
      
      // 并行加载所有数据
      const [klineData, hlData, historicLowsData] = await Promise.all([
        fetchStockKline(stockId, 'daily'),
        fetchStockHLAnalysis(stockId),
        fetchStockAllHistoricLows(stockId)
      ]);
      
      console.log('All data loaded successfully:');
      console.log('K-line data:', klineData);
      console.log('HL data:', hlData);
      console.log('Historic lows data:', historicLowsData);
      
      // 设置所有数据
      setKlineData(klineData);
      setHlData(hlData);
      setAllHistoricLows(historicLowsData);
      
      // 更新点位详细信息
      if (hlData) {
        updatePointDetails(hlData);
      }
      
      console.log('All state updated, chart should re-render');
      
      // 强制图表重新渲染
      setTimeout(() => {
        setChartKey(prev => prev + 1);
        console.log('Chart key updated, forcing re-render');
      }, 100);
      
    } catch (err) {
      console.error('数据加载失败:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 生成ECharts配置
  const getChartOption = () => {
    if (!klineData || !klineData.klines) {
      return {};
    }

    const klines = klineData.klines;
    
    // 准备K线数据 - 使用复权后的价格（不是raw字段）
    const data = klines.map(item => [
      parseFloat(item.open) || 0,      // 复权后的开盘价
      parseFloat(item.close) || 0,     // 复权后的收盘价
      parseFloat(item.lowest) || 0,    // 复权后的最低价
      parseFloat(item.highest) || 0,   // 复权后的最高价
      parseInt(item.volume) || 0       // 成交量
    ]);

    // 准备日期数据
    const dates = klines.map(item => item.date);

    // 准备投资点位数据
    const buyPoints = [];      // 买入点（蓝色）
    const sellWinPoints = [];  // 卖出盈利点（绿色）
    const sellLossPoints = []; // 卖出亏损点（红色）
    const referencePoints = []; // 历史低点（紫色菱形）

    if (hlData && hlData.results) {
      const results = hlData.results || [];
      
      console.log('Processing HL data, results count:', results.length);
      
      // 处理所有投资记录
      results.forEach((result, index) => {
        const investmentInfo = result.investment_info || {};
        const settlementInfo = result.settlement_info || {};
        
        console.log(`Processing result ${index}:`, {
          investmentInfo,
          settlementInfo,
          status: result.status
        });
        
        // 买入点
        if (investmentInfo.start_date && investmentInfo.purchase_price) {
          buyPoints.push([investmentInfo.start_date, investmentInfo.purchase_price]);
          console.log(`Added buy point: ${investmentInfo.start_date}, ${investmentInfo.purchase_price}`);
        }
        
        // 卖出点
        if (settlementInfo.exit_date && settlementInfo.exit_price) {
          if (result.status === 'win') {
            sellWinPoints.push([settlementInfo.exit_date, settlementInfo.exit_price]);
            console.log(`Added sell win point: ${settlementInfo.exit_date}, ${settlementInfo.exit_price}`);
          } else if (result.status === 'loss') {
            sellLossPoints.push([settlementInfo.exit_date, settlementInfo.exit_price]);
            console.log(`Added sell loss point: ${settlementInfo.exit_date}, ${settlementInfo.exit_price}`);
          }
        }
        
        // 历史低点参考（不再添加到散点，改为标记线）
        if (investmentInfo.historic_low_ref?.date && investmentInfo.historic_low_ref?.lowest_price) {
          // 不添加到散点，而是通过markLine显示
        }
      });
    } else {
      // 没有HL数据时，添加一些测试点位用于验证图表功能
      // 这些点位会在HL数据加载后被替换
      if (klines.length > 0) {
        const midIndex = Math.floor(klines.length / 2);
        const testDate = klines[midIndex].date;
        const testPrice = parseFloat(klines[midIndex].close);
        
        // 添加一个测试买入点
        buyPoints.push([testDate, testPrice]);
        
        // 添加一个测试卖出点
        sellWinPoints.push([testDate, testPrice * 1.1]);
        sellLossPoints.push([testDate, testPrice * 0.9]);
      }
    }
    
    // 添加调试日志
    console.log('Investment points generated:');
    console.log('buyPoints:', buyPoints);
    console.log('sellWinPoints:', sellWinPoints);
    console.log('sellLossPoints:', sellLossPoints);

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: function (params) {
          let result = '';
          params.forEach(param => {
            if (param.seriesType === 'candlestick') {
              result += `${param.name}<br/>
                        开盘: ${param.data[0]}<br/>
                        收盘: ${param.data[1]}<br/>
                        最低: ${param.data[2]}<br/>
                        最高: ${param.data[3]}<br/>
                        成交量: ${param.data[4]}<br/>`;
            } else if (param.seriesType === 'scatter') {
              if (param.seriesName === '买入点') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              } else if (param.seriesName === '卖出盈利') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              } else if (param.seriesName === '卖出亏损') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              } else if (param.seriesName === '历史低点') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              }
            }
          });
          return result;
        }
      },
      legend: {
        data: ['K线', '止损线', '止盈线', '买入点', '卖出盈利', '卖出亏损'],
        top: 30
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%'
      },
      xAxis: {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      yAxis: {
        scale: true,
        splitArea: {
          show: true
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 50,
          end: 100
        },
        {
          show: true,
          type: 'slider',
          top: '90%',
          start: 50,
          end: 100
        }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: data,
          itemStyle: {
            color: '#fd1050',
            color0: '#0cf49b',
            borderColor: '#fd1050',
            borderColor0: '#0cf49b'
          },
          // 添加历史低点标记线
          markLine: (() => {
            const lowPointLines = generateLowPointMarkLines();
            console.log('Generated markLine data for K-line series:', lowPointLines);
            return {
              silent: true,
              symbol: 'none',
              lineStyle: {
                color: '#666666', // 灰色
                width: 1,
                type: 'dashed'  // 虚线
              },
              data: lowPointLines
            };
          })()
        },
        // 辅助线系列（动态显示）
        {
          name: '辅助线',
          type: 'line',
          data: [],
          lineStyle: {
            color: '#ffa500',
            width: 2,
            type: 'dashed'
          },
          symbol: 'none',
          silent: true
        },
        {
          name: '买入点',
          type: 'scatter',
          data: buyPoints,
          symbolSize: 10,
          itemStyle: {
            color: '#1890ff'
          }
        },
        {
          name: '卖出盈利',
          type: 'scatter',
          data: sellWinPoints,
          symbolSize: 10,
          itemStyle: {
            color: '#52c41a'
          }
        },
        {
          name: '卖出亏损',
          type: 'scatter',
          data: sellLossPoints,
          symbolSize: 10,
          itemStyle: {
            color: '#ff4d4f'
          }
        },

      ]
    };

    return option;
  };

  return (
    <div className="page page-chart">
      <div className="card">
        <div className="card-header container">
          <h2>股票K线图与投资点位</h2>
          <div className="main-chart">
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="stockId">股票代码</label>
                <div>
                  <input
                    id="stockId"
                    type="text"
                    value={stockId}
                    onChange={(e) => setStockId(e.target.value)}
                    placeholder="例如: 000002.SZ"
                    required
                    style={{ width: '60%', display: 'inline-block' }}
                  />
                  <div style={{ display: 'inline-block', marginLeft: '1rem' }}>
                    <button 
                      onClick={handleLoadData} 
                      className="btn" 
                      disabled={loading}
                    >
                      {loading ? '加载中...' : '加载数据'}
                    </button>
                    <button 
                      onClick={() => {
                        if (chartRef.current) {
                          chartRef.current.getEchartsInstance().setOption(getChartOption());
                        }
                      }} 
                      className="btn" 
                      style={{ backgroundColor: '#ff4d4f', marginLeft: '.5rem' }}
                    >
                      清除辅助线
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          {error && <div className="error">{error}</div>}
          {loading && <div className="loading">正在加载数据...</div>}

        </div>
        
        {klineData && (
          <div className="card">
            <div className="card-header container">
              {hlData && hlData.statistics && (
                <p style={{ textAlign: 'center' }}>成功: <strong style={{ color: 'green', fontSize: '1.5rem' }}>{hlData.statistics?.success_count || 0}</strong> | 失败: <strong style={{ color: 'red', fontSize: '1.5rem' }}>{hlData.statistics?.fail_count || 0}</strong> | 模拟截止未完成: <strong style={{ color: '#333', fontSize: '1.5rem' }}>{hlData.statistics?.open_count || 0}</strong></p>
              )}
              {!hlData && (
                <p style={{ textAlign: 'center', color: '#666' }}>HL分析数据加载中...</p>
              )}
            </div>
            <div style={{ height: '600px' }}>
              <ReactECharts
                key={chartKey}
                ref={chartRef}
                option={getChartOption()}
                style={{ height: '100%' }}
                onEvents={{
                  click: (params) => {
                    if (params.seriesType === 'scatter') {
                      const pointDate = params.data[0];
                      const pointPrice = params.data[1];
                      // 查找对应的点位信息
                      let pointInfo = null;
                      for (const [key, info] of pointDetails.entries()) {
                        if (info.date === pointDate && Math.abs(info.price - pointPrice) < 0.01) {
                          pointInfo = info;
                          break;
                        }
                      }
                      
                                            if (pointInfo) {
                        // 根据点位类型显示不同的辅助线
                        if (pointInfo.type === 'buy' && pointInfo.target_win && pointInfo.target_loss) {
                          
                          // 买入点：显示止损止盈横线
                          const stopLossData = [
                            [pointInfo.date, pointInfo.target_loss], // 止损价格横线起点
                            [pointInfo.date, pointInfo.target_loss]   // 止损价格横线终点
                          ];
                          const takeProfitData = [
                            [pointInfo.date, pointInfo.target_win],  // 止盈价格横线起点
                            [pointInfo.date, pointInfo.target_win]   // 止盈价格横线终点
                          ];
                          
                          // 调试信息：显示pointInfo的完整内容
                          console.log('🔍 点击买入点，pointInfo内容:', pointInfo);
                          console.log('🔍 previous_low_points:', pointInfo.previous_low_points);
                          
                          // 显示历史低价信息
                          if (pointInfo.previous_low_points && pointInfo.previous_low_points.length > 0) {
                            const lowPrices = pointInfo.previous_low_points.map(p => p.price).join(', ');
                            console.log(`📊 买入点 ${pointInfo.date} 之前出现的历史低价: [${lowPrices}]`);
                            
                            // 在页面上显示信息（可以后续优化为弹窗或固定显示区域）
                            const infoDiv = document.createElement('div');
                            infoDiv.style.cssText = `
                              position: fixed;
                              top: 20px;
                              right: 20px;
                              background: rgba(0, 0, 0, 0.8);
                              color: white;
                              padding: 15px;
                              border-radius: 8px;
                              font-size: 14px;
                              z-index: 1000;
                              max-width: 300px;
                            `;
                            infoDiv.innerHTML = `
                              <div style="margin-bottom: 10px;"><strong>📊 买入点信息</strong></div>
                              <div>日期: ${pointInfo.date}</div>
                              <div>价格: ${pointInfo.price}</div>
                              <div style="margin-top: 10px;"><strong>之前出现的历史低价:</strong></div>
                              <div style="color: #ffa500;">[${lowPrices}]</div>
                              <div style="margin-top: 10px; font-size: 12px; color: #ccc;">
                                点击任意位置关闭
                              </div>
                            `;
                            
                            // 点击关闭
                            infoDiv.onclick = () => document.body.removeChild(infoDiv);
                            
                            // 3秒后自动关闭
                            setTimeout(() => {
                              if (document.body.contains(infoDiv)) {
                                document.body.removeChild(infoDiv);
                              }
                            }, 3000);
                            
                            document.body.appendChild(infoDiv);
                          } else {
                            console.log('⚠️ 没有找到previous_low_points信息');
                            // 显示提示信息
                            const infoDiv = document.createElement('div');
                            infoDiv.style.cssText = `
                              position: fixed;
                              top: 20px;
                              right: 20px;
                              background: rgba(255, 0, 0, 0.8);
                              color: white;
                              padding: 15px;
                              border-radius: 8px;
                              font-size: 14px;
                              z-index: 1000;
                              max-width: 300px;
                            `;
                            infoDiv.innerHTML = `
                              <div style="margin-bottom: 10px;"><strong>⚠️ 数据缺失</strong></div>
                              <div>买入点: ${pointInfo.date}</div>
                              <div>价格: ${pointInfo.price}</div>
                              <div style="margin-top: 10px; color: #ffcccc;">
                                没有找到历史低价信息
                              </div>
                              <div style="margin-top: 10px; font-size: 12px; color: #ccc;">
                                点击任意位置关闭
                              </div>
                            `;
                            
                            infoDiv.onclick = () => document.body.removeChild(infoDiv);
                            setTimeout(() => {
                              if (document.body.contains(infoDiv)) {
                                document.body.removeChild(infoDiv);
                              }
                            }, 3000);
                            
                            document.body.appendChild(infoDiv);
                          }
                          
                          const newOption = {
                            ...getChartOption(),
                            series: [
                              ...getChartOption().series.slice(0, 1), // K线
                              ...getChartOption().series.slice(2) // 其他点位
                            ]
                          };
                          
                          // 保留原有的历史低点markLine，并添加新的辅助线
                          const existingMarkLine = getChartOption().series[0].markLine || {};
                          const existingData = existingMarkLine.data || [];
                          
                          // 为K线系列添加markLine，合并原有的历史低点线和新的辅助线
                          newOption.series[0].markLine = {
                            silent: true,
                            symbol: 'none',
                            lineStyle: {
                              color: '#ff4d4f',
                              width: 2,
                              type: 'dashed'
                            },
                            data: [
                              // 保留原有的历史低点线
                              ...existingData,
                              // 添加新的辅助线
                              {
                                yAxis: pointInfo.target_loss,
                                name: '止损线'
                              },
                              {
                                yAxis: pointInfo.target_win,
                                name: '止盈线',
                                lineStyle: {
                                  color: '#52c410',
                                  width: 2,
                                  type: 'dashed'
                                }
                              },
                              // 添加当前点位线
                              {
                                yAxis: pointInfo.price,
                                name: '当前点位',
                                lineStyle: {
                                  color: '#1890ff',
                                  width: 2,
                                  type: 'dashed'
                                }
                              }
                            ]
                          };
                          
                          if (chartRef.current) {
                            const chart = chartRef.current.getEchartsInstance();
                            chart.setOption(newOption);
                          }
                        }
                      }
                    }
                  },
                  dblclick: (params) => {
                    // 双击清除辅助线
                                      if (chartRef.current) {
                    chartRef.current.getEchartsInstance().setOption(getChartOption());
                  }
                  }
                }}
              />
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}

export default StockChart;
