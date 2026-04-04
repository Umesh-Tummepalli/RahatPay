import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  StatusBar, 
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Button from '../components/Button';
import Input from '../components/Input';
import { useAuth } from '../context/AuthContext';

const AuthScreen = ({ navigation }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    phone: ''
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const { signIn, signUp, continueAsGuest } = useAuth();
  const insets = useSafeAreaInsets();

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    
    if (!isLogin) {
      if (!formData.name) {
        newErrors.name = 'Name is required';
      }
      
      if (!formData.phone) {
        newErrors.phone = 'Phone is required';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    
    setLoading(true);
    setErrors({});
    
    try {
      const result = isLogin 
        ? await signIn(formData.email, formData.password)
        : await signUp(formData.email, formData.password, formData.name, formData.phone);
      
      if (result.success) {
        navigation.navigate('KYC');
      } else {
        setErrors({ general: result.error });
      }
    } catch (error) {
      setErrors({ general: 'An unexpected error occurred' });
    } finally {
      setLoading(false);
    }
  };

  const handleSocialAuth = (provider) => {
    // TODO: Implement social authentication
    console.log(`${provider} authentication - to be implemented`);
  };

  const handleDemoAccess = async () => {
    setLoading(true);
    setErrors({});

    try {
      const result = await continueAsGuest();

      if (result.success) {
        navigation.reset({
          index: 0,
          routes: [{ name: 'Main' }],
        });
      }
    } catch (error) {
      setErrors({ general: 'Unable to open demo mode right now' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <KeyboardAvoidingView 
        style={styles.keyboardAvoid}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView 
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          <View style={[styles.content, { paddingTop: insets.top }]}>
            <View style={styles.logoContainer}>
              <Logo size="large" />
            </View>
            
            <View style={styles.formContainer}>
              <View style={styles.tabContainer}>
                <TouchableOpacity
                  style={[styles.tab, isLogin && styles.activeTab]}
                  onPress={() => setIsLogin(true)}
                >
                  <Text style={[styles.tabText, isLogin && styles.activeTabText]}>
                    Login
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.tab, !isLogin && styles.activeTab]}
                  onPress={() => setIsLogin(false)}
                >
                  <Text style={[styles.tabText, !isLogin && styles.activeTabText]}>
                    Sign Up
                  </Text>
                </TouchableOpacity>
              </View>
              
              <View style={styles.form}>
                {!isLogin && (
                  <Input
                    placeholder="Full Name"
                    value={formData.name}
                    onChangeText={(value) => handleInputChange('name', value)}
                    icon="person-outline"
                    error={errors.name}
                    style={styles.input}
                  />
                )}
                
                <Input
                  placeholder="Email Address"
                  value={formData.email}
                  onChangeText={(value) => handleInputChange('email', value)}
                  icon="mail-outline"
                  error={errors.email}
                  style={styles.input}
                />
                
                <Input
                  placeholder="Password"
                  value={formData.password}
                  onChangeText={(value) => handleInputChange('password', value)}
                  icon="lock-closed-outline"
                  secureTextEntry
                  error={errors.password}
                  style={styles.input}
                />
                
                {!isLogin && (
                  <Input
                    placeholder="Phone Number"
                    value={formData.phone}
                    onChangeText={(value) => handleInputChange('phone', value)}
                    icon="phone-portrait-outline"
                    error={errors.phone}
                    style={styles.input}
                  />
                )}
                
                {errors.general && (
                  <Text style={styles.errorText}>{errors.general}</Text>
                )}
                
                <Button
                  title={isLogin ? 'Sign In' : 'Create Account'}
                  onPress={handleSubmit}
                  loading={loading}
                  style={styles.button}
                />

                <Button
                  title="Open Demo App"
                  onPress={handleDemoAccess}
                  variant="outline"
                  style={styles.button}
                />
                
                {isLogin && (
                  <>
                    <View style={styles.dividerContainer}>
                      <View style={styles.divider} />
                      <Text style={styles.dividerText}>OR</Text>
                      <View style={styles.divider} />
                    </View>
                    
                    <View style={styles.socialButtonsContainer}>
                      <Button
                        title="Continue with Google"
                        onPress={() => handleSocialAuth('Google')}
                        variant="outline"
                        style={styles.socialButton}
                        icon="logo-google"
                      />
                      
                      <Button
                        title="Continue with Apple"
                        onPress={() => handleSocialAuth('Apple')}
                        variant="outline"
                        style={styles.socialButton}
                        icon="logo-apple"
                      />
                    </View>
                  </>
                )}
                
                <View style={styles.switchAuth}>
                  <TouchableOpacity onPress={() => setIsLogin(!isLogin)}>
                    <Text style={styles.switchAuthText}>
                      {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Login"}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          </View>
          </ScrollView>
        </KeyboardAvoidingView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  keyboardAvoid: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingBottom: 40,
  },
  logoContainer: {
    alignItems: 'center',
    marginTop: 60,
    marginBottom: 40,
  },
  formContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: COLORS.white,
    borderRadius: 25,
    padding: 3,
    marginTop: 20,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  tab: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    borderRadius: 22,
  },
  activeTab: {
    backgroundColor: COLORS.primary,
  },
  tabText: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.grey,
  },
  activeTabText: {
    color: COLORS.white,
  },
  form: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  input: {
    marginBottom: 12,
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
  dividerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: COLORS.lightGrey,
  },
  dividerText: {
    paddingHorizontal: 16,
    fontSize: 12,
    color: COLORS.grey,
    fontWeight: '500',
  },
  socialButtonsContainer: {
    gap: 12,
    marginBottom: 20,
  },
  socialButton: {
    flex: 1,
  },
  switchAuth: {
    alignItems: 'center',
  },
  switchAuthText: {
    fontSize: 14,
    color: COLORS.primary,
    fontWeight: '500',
  }
});

export default AuthScreen;
