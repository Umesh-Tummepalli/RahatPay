import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../utils/constants';

const Card = ({ children, style, padding = 'medium' }) => {
  const getPaddingStyle = () => {
    switch (padding) {
      case 'small':
        return { padding: 12 };
      case 'medium':
        return { padding: 20 };
      case 'large':
        return { padding: 24 };
      default:
        return { padding: 20 };
    }
  };

  return (
    <View style={[styles.card, getPaddingStyle(), style]}>
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.white,
    borderRadius: 20,
  },
});

export default Card;
