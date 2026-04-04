import React from 'react';
import { View, StyleSheet, Image } from 'react-native';
import { COLORS } from '../utils/constants';

const Logo = ({ size = 'medium' }) => {
  const getLogoSize = () => {
    switch (size) {
      case 'tiny':
        return { imageSize: 60 };
      case 'small':
        return { imageSize: 120 };
      case 'medium':
        return { imageSize: 180 };
      case 'large':
        return { imageSize: 240 };
      default:
        return { imageSize: 180 };
    }
  };

  const { imageSize } = getLogoSize();

  return (
    <View style={styles.container}>
      <Image
        source={require('../../assets/logo.png')}
        style={[styles.logoImage, { width: imageSize, height: imageSize, marginTop: 12 }]}
        resizeMode="contain"
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoImage: {
    marginBottom: 16,
  },
});

export default Logo;
