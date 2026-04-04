import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  StatusBar, 
  ScrollView,
  Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';

const KYCVerificationScreen = ({ navigation }) => {
  const [formData, setFormData] = useState({
    aadhaar: '',
    pan: ''
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const { user } = useAuth();

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.aadhaar) {
      newErrors.aadhaar = 'Aadhaar is required';
    } else if (!/^\d{12}$/.test(formData.aadhaar)) {
      newErrors.aadhaar = 'Invalid Aadhaar format';
    }
    
    if (!formData.pan) {
      newErrors.pan = 'PAN is required';
    } else if (!/^[A-Z]{5}[0-9]{4}$/.test(formData.pan)) {
      newErrors.pan = 'Invalid PAN format (e.g., ABCDE1234)';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    
    setLoading(true);
    
    // Mock KYC submission
    setTimeout(() => {
      Alert.alert(
        'KYC Verification Successful',
        'Your identity has been verified successfully!',
        [{ text: 'OK', onPress: () => navigation.navigate('TrialIntro') }]
      );
      setLoading(false);
    }, 2000);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          <Logo size="medium" />
          
          <Card style={styles.card}>
            <View style={styles.header}>
              <View style={styles.iconContainer}>
                <Ionicons name="shield-checkmark-outline" size={24} color={COLORS.primary} />
              </View>
              <Text style={styles.headerTitle}>KYC Verification</Text>
            </View>
            
            <Text style={styles.subtitle}>
              Complete your identity verification to activate your insurance coverage
            </Text>
            
            <View style={styles.form}>
              <Input
                placeholder="Aadhaar Number"
                value={formData.aadhaar}
                onChangeText={(value) => handleInputChange('aadhaar', value)}
                icon="card-outline"
                error={errors.aadhaar}
                style={styles.input}
                maxLength={12}
                keyboardType="numeric"
              />
              
              <Input
                placeholder="PAN Number"
                value={formData.pan}
                onChangeText={(value) => handleInputChange('pan', value)}
                icon="document-text-outline"
                error={errors.pan}
                style={styles.input}
                maxLength={10}
                autoCapitalize="characters"
              />
              
              {Object.keys(errors).length > 0 && (
                <Text style={styles.errorText}>
                  Please fix the errors above
                </Text>
              )}
              
              <Button
                title="Submit KYC"
                onPress={handleSubmit}
                loading={loading}
                style={styles.button}
              />
            </View>
            
            <View style={styles.infoContainer}>
              <Text style={styles.infoTitle}>Why we need this information?</Text>
              <Text style={styles.infoText}>
                • Aadhaar helps us verify your identity{'\n'}
                • PAN is required for insurance compliance{'\n'}
                • Your information is secure and encrypted
              </Text>
            </View>
          </Card>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  content: {
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 20,
  },
  card: {
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: `${COLORS.primary}20`,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.black,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.grey,
    marginBottom: 24,
    textAlign: 'center',
    lineHeight: 22,
  },
  form: {
    marginBottom: 24,
  },
  input: {
    marginBottom: 16,
  },
  errorText: {
    color: '#FF6B6B',
    fontSize: 14,
    marginBottom: 16,
    textAlign: 'center',
  },
  button: {
    marginBottom: 16,
  },
  infoContainer: {
    backgroundColor: `${COLORS.primary}10`,
    borderRadius: 12,
    padding: 16,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 12,
  },
  infoText: {
    fontSize: 14,
    color: COLORS.grey,
    lineHeight: 20,
  }
});

export default KYCVerificationScreen;
