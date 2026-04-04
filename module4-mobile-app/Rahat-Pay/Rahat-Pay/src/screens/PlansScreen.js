/**
 * PlansScreen.js — delegates to PlanSelectionScreen (server-driven).
 * This file exists because the navigation stack uses 'Plans' as the route name.
 */
import React from 'react';
import PlanSelectionScreen from './PlanSelectionScreen';

const PlansScreen = (props) => <PlanSelectionScreen {...props} />;

export default PlansScreen;
