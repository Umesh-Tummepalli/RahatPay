import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';

const TabIcon = ({ name, label, focused, onPress }) => {
  return (
    <TouchableOpacity 
      style={styles.container}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Ionicons
        name={name}
        size={24}
        color={focused ? COLORS.primary : COLORS.grey}
      />
      <Text style={[styles.label, focused && styles.labelFocused]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    paddingVertical: 8,
  },
  label: {
    fontSize: 12,
    color: COLORS.grey,
    marginTop: 4,
  },
  labelFocused: {
    color: COLORS.primary,
  },
});

export default TabIcon;
