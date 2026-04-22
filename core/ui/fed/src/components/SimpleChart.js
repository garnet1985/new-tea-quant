import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

const SimpleChart = () => {
  
  const chartRef = useRef(null);

  useEffect(() => {
    
    try {
      // 创建ECharts实例
      const chart = echarts.init(chartRef.current);
      
      // 简单的测试配置
      const option = {
        title: {
          text: '测试图表'
        },
        xAxis: {
          type: 'category',
          data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        },
        yAxis: {
          type: 'value'
        },
        series: [{
          data: [820, 932, 901, 934, 1290, 1330, 1320],
          type: 'line'
        }]
      };

      console.log('Setting chart option:', option);
      chart.setOption(option);
      console.log('Chart rendered successfully');

    } catch (error) {
      console.error('Error rendering simple chart:', error);
    }
  }, []);

  return (
    <div style={{ width: '100%', height: '400px', border: '2px solid red' }}>
      <div ref={chartRef} style={{ width: '100%', height: '100%' }}></div>
    </div>
  );
};

export default SimpleChart;
