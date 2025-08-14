#!/usr/bin/env python3
"""
Simple debug script for trend check
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.strategy.historicLow.strategy_settings import invest_settings

def test_trend_check():
    """Test trend check logic"""
    print("Testing trend check logic...")
    
    service = HistoricLowService()
    
    # Test data - simulate daily records
    test_data = []
    for i in range(100):
        # Create some test price data
        price = 6.5 + (i - 50) * 0.01  # Around 6.5 with small variation
        test_data.append({
            'date': f'2024{str(i//30+7).zfill(2)}{str(i%30+1).zfill(2)}',
            'close': price,
            'lowest': price * 0.99,
            'highest': price * 1.01
        })
    
    print(f"Created {len(test_data)} test records")
    
    # Test trend check
    result = service.is_trend_too_steep(test_data)
    print(f"Trend check result: {result}")
    
    # Show settings
    threshold = invest_settings['goal']['invest_reference_day_distance_threshold']
    print(f"Threshold days: {threshold}")

if __name__ == "__main__":
    test_trend_check()
