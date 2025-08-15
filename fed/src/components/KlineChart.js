import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

const KlineChart = ({ data, stockId }) => {
  alert('KlineChart组件被渲染，props: ' + JSON.stringify({ data: data ? '有数据' : '无数据', stockId }));
  
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    alert('=== KlineChart useEffect 开始 ===');
    alert('数据: ' + (data ? '有数据' : '无数据') + ', 股票ID: ' + stockId);
    
    if (!data || !data.klines || data.klines.length === 0) {
      alert('没有数据，退出');
      return;
    }

    // 销毁之前的图表实例
    if (chartInstance.current) {
      chartInstance.current.dispose();
    }

    try {
      // 创建ECharts实例
      chartInstance.current = echarts.init(chartRef.current);
      
      // 准备数据 - 按照ECharts K线图要求的数据格式
      const dates = data.klines.map(kline => kline.date);
      
      // K线数据格式：[open, close, lowest, highest]
      const klineData = data.klines.map(kline => {
        const open = parseFloat(kline.open) || 0;
        const close = parseFloat(kline.close) || 0;
        const lowest = parseFloat(kline.lowest) || 0;
        const highest = parseFloat(kline.highest) || 0;
        
        console.log(`原始数据: open=${kline.open}, close=${kline.close}, lowest=${kline.lowest}, highest=${kline.highest}`);
        console.log(`转换后: [${open}, ${close}, ${lowest}, ${highest}]`);
        
        return [open, close, lowest, highest];
      });

      // 成交量数据
      const volumeData = data.klines.map(kline => parseInt(kline.volume) || 0);

      console.log('K线数据:', klineData);
      console.log('成交量数据:', volumeData);
      console.log('日期数据:', dates);

      // 验证数据
      if (klineData.length === 0 || klineData.some(item => item.some(val => isNaN(val)))) {
        console.error('Invalid K线数据:', klineData);
        return;
      }

      // 检查数据范围
      const allPrices = klineData.flat();
      const minPrice = Math.min(...allPrices);
      const maxPrice = Math.max(...allPrices);
      console.log(`价格范围: ${minPrice} - ${maxPrice}`);

      // 测试数据 - 验证ECharts是否能正常显示K线图
      const testData = [
        [20, 34, 10, 38],
        [40, 35, 30, 50],
        [31, 38, 31, 44],
        [38, 15, 5, 42]
      ];
      console.log('测试数据:', testData);

      // 按照ECharts官方文档配置K线图
      const option = {
        title: {
          text: `${stockId} 股票K线图`,
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: dates
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: 'K线',
            type: 'candlestick',
            data: klineData
          }
        ]
      };

      // 先测试测试数据
      const testOption = {
        title: {
          text: '测试K线图',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: ['Mon', 'Tue', 'Wed', 'Thu']
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: '测试K线',
            type: 'candlestick',
            data: testData
          }
        ]
      };

      console.log('测试配置:', testOption);
      console.log('实际配置:', option);

      // 先渲染测试图表
      chartInstance.current.setOption(testOption);
      console.log('测试图表渲染完成');

      // 检查测试图表是否成功渲染
      setTimeout(() => {
        const testChartData = chartInstance.current.getOption();
        console.log('测试图表当前配置:', testChartData);
        
        // 尝试渲染实际数据
        try {
          // 确保数据格式完全正确
          const cleanKlineData = klineData.map((item, index) => {
            if (item.length !== 4) {
              console.error(`数据项 ${index} 格式错误:`, item);
              return null;
            }
            const [open, close, lowest, highest] = item;
            if (isNaN(open) || isNaN(close) || isNaN(lowest) || isNaN(highest)) {
              console.error(`数据项 ${index} 包含NaN:`, item);
              return null;
            }
            return [open, close, lowest, highest];
          }).filter(Boolean);

          console.log('清理后的K线数据:', cleanKlineData);

          if (cleanKlineData.length === 0) {
            console.error('没有有效的K线数据');
            return;
          }

          // 使用清理后的数据重新配置
          const cleanOption = {
            title: {
              text: `${stockId} 股票K线图 (${cleanKlineData.length}条数据)`,
              left: 'center'
            },
            tooltip: {
              trigger: 'axis'
            },
            xAxis: {
              type: 'category',
              data: dates.slice(0, cleanKlineData.length)
            },
            yAxis: {
              type: 'value'
            },
            series: [
              {
                name: 'K线',
                type: 'candlestick',
                data: cleanKlineData
              }
            ]
          };

          console.log('清理后的配置:', cleanOption);
          chartInstance.current.setOption(cleanOption, true); // 第二个参数true表示完全替换
          console.log('实际图表渲染完成');
          
        } catch (error) {
          console.error('渲染实际图表时出错:', error);
        }
      }, 2000);

    } catch (error) {
      console.error('Error rendering chart:', error);
    }

    // 响应式处理
    const handleResize = () => {
      if (chartInstance.current) {
        chartInstance.current.resize();
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartInstance.current) {
        chartInstance.current.dispose();
      }
    };
  }, [data, stockId]);

  if (!data || !data.klines || data.klines.length === 0) {
    return <div>暂无数据</div>;
  }

  return (
    <div style={{ width: '100%', height: '600px', border: '1px solid #ccc' }}>
      <div ref={chartRef} style={{ width: '100%', height: '100%' }}></div>
    </div>
  );
};

export default KlineChart;
