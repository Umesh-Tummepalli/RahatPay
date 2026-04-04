import React from 'react';
import { Text, StyleSheet, TouchableOpacity } from 'react-native';
import { COLORS } from '../utils/constants';

const Button = ({ 
  title, 
  onPress, 
  variant = 'primary', 
  size = 'medium', 
  loading = false, 
  disabled = false,
  style 
}) => {
  const getButtonStyle = () => {
    const baseStyle = [styles.button];
    
    if (variant === 'primary') {
      baseStyle.push({ backgroundColor: COLORS.primary });
    } else if (variant === 'secondary') {
      baseStyle.push({ backgroundColor: COLORS.white, borderWidth: 1, borderColor: COLORS.primary });
    } else if (variant === 'outline') {
      baseStyle.push({ backgroundColor: 'transparent', borderWidth: 1, borderColor: COLORS.primary });
    }
    
    if (size === 'small') {
      baseStyle.push({ paddingVertical: 8, paddingHorizontal: 16 });
    } else if (size === 'large') {
      baseStyle.push({ paddingVertical: 20, paddingHorizontal: 32 });
    }
    
    if (disabled) {
      baseStyle.push({ opacity: 0.5 });
    }
    
    return baseStyle;
  };

  const getTextStyle = () => {
    const baseStyle = [styles.text];
    
    if (variant === 'primary') {
      baseStyle.push({ color: COLORS.white });
    } else {
      baseStyle.push({ color: COLORS.primary });
    }
    
    return baseStyle;
  };

  return (
    <TouchableOpacity
      style={[getButtonStyle(), style]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.8}
    >
      <Text style={getTextStyle()}>{loading ? 'Loading...' : title}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    borderRadius: 25,
    paddingVertical: 16,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
});

export default Button;
