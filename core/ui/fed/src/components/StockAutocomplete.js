import React, { useState, useEffect, useRef } from 'react';

function StockAutocomplete({ value, onChange, disabled, autoSearch = true }) {
  const [inputValue, setInputValue] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const isSelectingRef = useRef(false);
  const isMountedRef = useRef(false);

  useEffect(() => {
    setInputValue(value || '');
    // 首次挂载时不触发搜索（避免编辑模式下自动触发）
    if (!isMountedRef.current) {
      isMountedRef.current = true;
    }
  }, [value]);

  useEffect(() => {
    // 如果disabled或autoSearch为false，不自动搜索
    if (disabled || !autoSearch) {
      setShowSuggestions(false);
      return;
    }

    const handleSearch = async () => {
      // 如果正在选择中，不进行搜索
      if (isSelectingRef.current) {
        return;
      }

      // 首次挂载时不触发搜索
      if (!isMountedRef.current) {
        return;
      }

      if (inputValue.length < 2) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }

      try {
        const response = await fetch(`http://localhost:5001/api/investment/stocks/search/${encodeURIComponent(inputValue)}`);
        const data = await response.json();
        
        if (data.success) {
          setSuggestions(data.data || []);
          setShowSuggestions(true);
        }
      } catch (err) {
        console.error('搜索股票失败:', err);
      }
    };

    const timeoutId = setTimeout(handleSearch, 300);
    return () => clearTimeout(timeoutId);
  }, [inputValue, disabled, autoSearch]);

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    onChange(newValue);
  };

  const handleSelect = (stock) => {
    // 设置标志，阻止后续搜索
    isSelectingRef.current = true;
    
    setInputValue(stock.id);
    onChange(stock.id);
    setShowSuggestions(false);
    setSuggestions([]);
    
    // 短暂延迟后重置标志
    setTimeout(() => {
      isSelectingRef.current = false;
    }, 500);
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[selectedIndex]);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const handleBlur = (e) => {
    // 延迟隐藏，让点击事件先触发
    setTimeout(() => {
      // 如果用户点击的不是建议列表，才隐藏
      if (!e.relatedTarget?.closest('.autocomplete-suggestions')) {
        setShowSuggestions(false);
      }
    }, 300);
  };

  return (
    <div className="autocomplete-container">
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => inputValue.length >= 2 && setShowSuggestions(true)}
        onBlur={handleBlur}
        disabled={disabled}
        placeholder="例: 000001.SZ 或 平安银行"
        className="form-control"
      />
      {showSuggestions && suggestions.length > 0 && (
        <ul className="autocomplete-suggestions" ref={listRef}>
          {suggestions.map((stock, index) => (
            <li
              key={stock.id}
              className={`autocomplete-item ${index === selectedIndex ? 'selected' : ''}`}
              onMouseDown={(e) => {
                e.preventDefault(); // 防止 input 失去焦点
                handleSelect(stock);
              }}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className="stock-id-suggestion">{stock.id}</div>
              <div className="stock-name-suggestion">{stock.name}</div>
              {stock.industry && (
                <div className="stock-industry-suggestion">{stock.industry}</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default StockAutocomplete;

