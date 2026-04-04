// Validation utilities
export const validateAadhaar = (aadhaar) => {
  const aadhaarRegex = /^[0-9]{12}$/;
  return aadhaarRegex.test(aadhaar);
};

export const validatePAN = (pan) => {
  const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
  return panRegex.test(pan);
};

export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePhone = (phone) => {
  const phoneRegex = /^[6-9]\d{9}$/;
  return phoneRegex.test(phone);
};

export const validatePassword = (password) => {
  return password.length >= 6;
};

// Format utilities
export const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
};

export const formatDateTime = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0
  }).format(amount);
};

export const formatNumber = (number) => {
  return new Intl.NumberFormat('en-IN').format(number);
};

// Masking utilities
export const maskAadhaar = (aadhaar) => {
  if (!aadhaar || aadhaar.length !== 12) return 'XXXX XXXX XXXX';
  return `${aadhaar.substring(0, 4)} XXXX ${aadhaar.substring(8)}`;
};

export const maskPAN = (pan) => {
  if (!pan || pan.length !== 10) return 'XXXXX****X';
  return `${pan.substring(0, 5)}****${pan.substring(9)}`;
};

export const maskPhone = (phone) => {
  if (!phone || phone.length !== 10) return 'XXXXXXXXXX';
  return `XXXXXX${phone.substring(6)}`;
};

// Date utilities
export const addDays = (date, days) => {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
};

export const getDaysRemaining = (endDate) => {
  const end = new Date(endDate);
  const now = new Date();
  const diffTime = end - now;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
};

export const isDateExpired = (endDate) => {
  return new Date() > new Date(endDate);
};

// Color utilities
export const getCoverageColor = (percentage) => {
  if (percentage > 60) return '#4CAF50'; // Green
  if (percentage > 30) return '#FF9800'; // Orange
  return '#F44336'; // Red
};

export const getStatusColor = (status) => {
  switch (status) {
    case 'active':
      return '#4CAF50';
    case 'expired':
      return '#F44336';
    case 'pending':
      return '#FF9800';
    default:
      return '#666666';
  }
};

// Event utilities
export const getEventConfig = (eventType) => {
  const configs = {
    flood: {
      name: 'Flood',
      amount: 500,
      icon: 'water',
      color: '#2196F3',
      severity: 'high'
    },
    rain: {
      name: 'Heavy Rain',
      amount: 300,
      icon: 'rainy',
      color: '#03A9F4',
      severity: 'medium'
    },
    aqi: {
      name: 'AQI Spike',
      amount: 200,
      icon: 'cloudy',
      color: '#9C27B0',
      severity: 'medium'
    },
    cyclone: {
      name: 'Cyclone Alert',
      amount: 600,
      icon: 'thunderstorm',
      color: '#FF5722',
      severity: 'high'
    }
  };
  
  return configs[eventType] || null;
};

// Plan utilities
export const getPlanConfig = (planId) => {
  const plans = {
    kavach: {
      name: 'Kavach',
      coverage: 80,
      premium: 1.0,
      color: '#4ECDC4',
      description: 'Basic coverage for essential protection'
    },
    suraksha: {
      name: 'Suraksha',
      coverage: 90,
      premium: 1.8,
      color: '#6B9071',
      description: 'Comprehensive coverage for most scenarios'
    },
    raksha: {
      name: 'Raksha',
      coverage: 100,
      premium: 2.5,
      color: '#FF6B6B',
      description: 'Maximum coverage with premium benefits'
    }
  };
  
  return plans[planId] || null;
};

// Storage utilities
export const storage = {
  set: async (key, value) => {
    try {
      const jsonValue = JSON.stringify(value);
      // In a real app, you'd use AsyncStorage or SecureStore
      localStorage.setItem(key, jsonValue);
    } catch (error) {
      console.error('Error storing data:', error);
    }
  },

  get: async (key) => {
    try {
      const jsonValue = localStorage.getItem(key);
      return jsonValue != null ? JSON.parse(jsonValue) : null;
    } catch (error) {
      console.error('Error retrieving data:', error);
      return null;
    }
  },

  remove: async (key) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing data:', error);
    }
  }
};

// Error handling utilities
export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    return {
      message: error.response.data.message || 'Server error occurred',
      status: error.response.status
    };
  } else if (error.request) {
    // Request was made but no response received
    return {
      message: 'Network error. Please check your connection.',
      status: 0
    };
  } else {
    // Something else happened
    return {
      message: error.message || 'An unexpected error occurred',
      status: -1
    };
  }
};

// Debounce utility
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// Throttle utility
export const throttle = (func, limit) => {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};
