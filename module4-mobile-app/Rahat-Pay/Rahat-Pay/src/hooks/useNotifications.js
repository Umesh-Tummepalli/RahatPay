import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Alert,
  Platform
} from 'react-native';
import * as Notifications from 'expo-notifications';

// Configure notifications
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export const useNotifications = () => {
  const [pushToken, setPushToken] = useState(null);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    registerForPushNotifications();
    
    const notificationListener = Notifications.addNotificationReceivedListener(
      notification => {
        setNotification(notification);
      }
    );

    return () => {
      Notifications.removeNotificationSubscription(notificationListener);
    };
  }, []);

  const registerForPushNotifications = async () => {
    try {
      // Request permissions
      const { status } = await Notifications.requestPermissionsAsync();
      if (status !== 'granted') {
        console.log('Permission not granted');
        return;
      }

      // Get push token
      const token = await Notifications.getExpoPushTokenAsync();
      if (token) {
        setPushToken(token.data);
        console.log('Expo push token:', token.data);
      }
    } catch (error) {
      console.error('Error registering for push notifications:', error);
    }
  };

  const sendLocalNotification = (title, body) => {
    Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: 'default',
      },
      trigger: null, // Show immediately
    });
  };

  const sendEventNotification = (eventType, eventData) => {
    const title = 'RahatPay Event Alert';
    const body = `${eventType}: ${eventData.description}`;
    sendLocalNotification(title, body);
  };

  return {
    pushToken,
    notification,
    sendLocalNotification,
    sendEventNotification,
  };
};
