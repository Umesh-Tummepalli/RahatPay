import React, { useState, useEffect } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi } from "../hooks/useApi";

// Mock data for demo purposes when backend is unavailable
const MOCK_FRAUD_ALERTS = [
  {
    claim_id: 8819,
    rider_id: 2088,
    reason: "Rider R-2088 artificially worked 18-hour days during their 4-week seasoning period to inflate their baseline_weekly_income from ₹3,500 to ₹14,200, then filed a claim on Day 3 of actual work.",
    risk_score: 0.94,
    exploit_type: "baseline_inflation",
    detection_method: "AIRA Behavioral Analysis",
    action_taken: "Baseline reset to city median. Account flagged for manual review.",
    status: "in_review"
  },
  {
    claim_id: 8820,
    rider_id: 1542,
    reason: "GPS coordinates show rider at home location (consistent SSID pattern) but claims to be in flood zone. Accelerometer shows no movement for 4 hours.",
    risk_score: 0.97,
    exploit_type: "gps_spoofing",
    detection_method: "Sensor Fusion Cross-Check",
    action_taken: "Claim auto-rejected. Trust score reduced to 15.",
    status: "in_review"
  },
  {
    claim_id: 8821,
    rider_id: 3301,
    reason: "Rider filed claims for 4 out of last 5 rain events, all during last 30 minutes of shift. Statistical anomaly: 92% claim rate vs 18% zone average.",
    risk_score: 0.88,
    exploit_type: "anomaly",
    detection_method: "Isolation Forest",
    action_taken: "Flagged for manual review. Extended verification required.",
    status: "in_review"
  }
];

export default function Fraud() {
  // Module 3: Live claims (in_review status for fraud review)
  const { data: allClaims, loading: claimsLoading, error: claimsError } = useApi(
    '/admin/claims/live',
    [],
    { baseUrl: 'module3' }
  );

  // Module 2: Model metadata
  const { data: modelInfo, loading: modelLoading, error: modelError } = useApi(
    '/api/model/info',
    null,
    { baseUrl: 'module2' }
  );

  const [usingMockData, setUsingMockData] = useState(false);
  const [mockDataReason, setMockDataReason] = useState("");

  // Attack simulation state
  const [attackType, setAttackType] = useState("gps_spoofing");
  const [attackLoading, setAttackLoading] = useState(false);
  const [attackResult, setAttackResult] = useState(null);

  // Filter in_review claims and extract fraud signals
  const inReviewClaims = Array.isArray(allClaims)
    ? allClaims.filter(c => c.status === "in_review").map(claim => {
        // Extract fraud signals if present
        const signals = [];
        if (claim.gate_results?.fraud_review) {
          const review = claim.gate_results.fraud_review;
          if (review.risk_score) signals.push(`Risk: ${(review.risk_score * 100).toFixed(0)}%`);
          if (review.reasons) {
            const reasons = Array.isArray(review.reasons) ? review.reasons : [review.reasons];
            signals.push(...reasons);
          }
        }
        return { ...claim, fraud_signals: signals };
      })
    : [];

  // Handle backend unavailability gracefully
  useEffect(() => {
    if ((claimsError && !inReviewClaims.length) || (modelError && !modelInfo)) {
      const reasons = [];
      if (claimsError) reasons.push("Module 3 claims");
      if (modelError) reasons.push("Module 2 model");
      
      if (reasons.length > 0) {
        setUsingMockData(true);
        setMockDataReason(`${reasons.join(" + ")} unavailable. Showing demo data.`);
      }
    } else {
      setUsingMockData(false);
    }
  }, [claimsError, modelError, inReviewClaims.length, modelInfo]);

  const handleSimulateAttack = async () => {
    setAttackLoading(true);
    setAttackResult(null);
    try {
      const res = await fetch("http://localhost:8001/admin/simulate-attack", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer admin_token"
        },
        body: JSON.stringify({ attack_type: attackType })
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setAttackResult(data);
    } catch (err) {
      console.error("Failed to simulate attack:", err);
      setAttackResult({ error: "Failed to simulate attack. Make sure the backend is running on port 8001." });
    } finally {
      setAttackLoading(false);
    }
  };

  // Display data: prefer live if available, fall back to mock
  const displayClaims = (inReviewClaims.length > 0 || !usingMockData) ? inReviewClaims : MOCK_FRAUD_ALERTS;
  const highRiskCount = displayClaims.filter(c => (c.risk_score || 0) > 0.95).length;

  const exploitLabels = {
    gps_spoofing: "GPS Spoofing",
    baseline_inflation: "Baseline Inflate",
    velocity_exploit: "Velocity Exploit",
    collusion_ring: "Collusion Ring",
    anomaly: "Anomaly",
  };

  const exploitColors = {
    gps_spoofing: "red",
    baseline_inflation: "amber",
    velocity_exploit: "red",
    collusion_ring: "red",
    anomaly: "amber",
  };

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Fraud detection & Attack simulation
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard 
            title="Claims in review" 
            value={claimsLoading ? "..." : displayClaims.length} 
            subtext="Fraud signals detected" 
            trend={displayClaims.length > 0 ? "warn" : "none"} 
          />
          <MetricCard 
            title="Attack types covered" 
            value="4" 
            subtext="GPS · Baseline · Velocity · Collusion" 
            trend="none" 
          />
          <MetricCard 
            title="High-risk alerts" 
            value={claimsLoading ? "..." : highRiskCount} 
            subtext="Score > 0.95" 
            trend="none" 
          />
          <MetricCard 
            title="Detection methods" 
            value={modelLoading ? "..." : (modelInfo?.detection_methods_count || "3")} 
            subtext="Active models" 
            trend="none" 
          />
        </div>
        
        {usingMockData && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md text-xs text-blue-800">
            ℹ️ <strong>Demo Mode:</strong> {mockDataReason} Start Module 3 (port 8003) and Module 2 (port 8002) for live data.
          </div>
        )}
        {(claimsError || modelError) && !usingMockData && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800">
            ⚠️ Some backends unavailable. Showing available data.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Attack Simulation Panel */}
        <Card className="border-t-4 border-t-red-500 shadow-[0_4px_20px_-4px_rgba(239,68,68,0.15)]">
          <CardHeader>
            <CardTitle>⚡ Attack Simulator</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-slate-500">Simulate fraud attacks to demonstrate RahatPay's detection pipeline and countermeasures.</p>

            <div>
              <label className="text-[10px] font-medium text-slate-500 uppercase">Attack Type</label>
              <select
                value={attackType}
                onChange={e => setAttackType(e.target.value)}
                className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-xs outline-none"
              >
                <option value="gps_spoofing">🛰️ GPS Spoofing Attack</option>
                <option value="baseline_inflation">📈 Baseline Inflation Exploit</option>
                <option value="velocity_exploit">⚡ Velocity / Rate-Limit Exploit</option>
                <option value="collusion_ring">🔗 Collusion Ring Detection</option>
              </select>
            </div>

            <Button onClick={handleSimulateAttack} disabled={attackLoading} variant="destructive" className="w-full font-medium tracking-wide">
              {attackLoading ? "Running Attack..." : "⚡ SIMULATE ATTACK"}
            </Button>

            {attackResult && !attackResult.error && (
              <div className="mt-3 p-3 rounded-md bg-red-50 border border-red-200 text-xs space-y-2">
                <h4 className="font-bold text-red-800 text-sm">{attackResult.title}</h4>
                <p className="text-red-700 leading-relaxed">{attackResult.description}</p>

                <div className="mt-2">
                  <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Detection Method</p>
                  <p className="text-slate-700 font-medium">{attackResult.detection_method}</p>
                </div>

                <div className="mt-2">
                  <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Evidence Chain</p>
                  <ul className="space-y-1">
                    {attackResult.evidence?.map((e, i) => (
                      <li key={i} className="flex gap-2 text-slate-600">
                        <span className="text-red-400 shrink-0">▸</span>
                        <span>{e}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                  <p className="text-[10px] font-bold text-green-700 uppercase mb-1">✅ Countermeasure Applied</p>
                  <p className="text-green-800 font-medium">{attackResult.countermeasure}</p>
                </div>
              </div>
            )}
            {attackResult?.error && (
              <div className="mt-2 p-2 rounded bg-red-100 text-red-700 text-xs">{attackResult.error}</div>
            )}
          </CardContent>
        </Card>

        {/* Claims in Review Feed */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>In-review claims feed (Module 3)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {claimsLoading && displayClaims.length === 0 ? (
              <div className="text-sm text-slate-500">Loading claims...</div>
            ) : displayClaims.length > 0 ? (
              <div className="max-h-[400px] overflow-y-auto space-y-3">
                {displayClaims.map((claim, i) => (
                  <div key={claim.claim_id || i} className="flex gap-3 border-b border-slate-100 pb-3 last:border-0">
                    <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${(claim.risk_score || 0) > 0.9 ? 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]' : 'bg-amber-400'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono font-bold text-xs text-slate-800">
                          {claim.claim_id ? `C-${claim.claim_id}` : `R-${claim.rider_id}`}
                        </span>
                        {claim.exploit_type && (
                          <Badge variant={exploitColors[claim.exploit_type] || "gray"}>
                            {exploitLabels[claim.exploit_type] || claim.exploit_type}
                          </Badge>
                        )}
                        {claim.risk_score && (
                          <span className="ml-auto font-mono text-[10px] text-slate-400">{(claim.risk_score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-600 leading-relaxed">
                        {claim.reason?.substring(0, 120)}{claim.reason?.length > 120 ? '...' : ''}
                      </p>
                      
                      {/* Display fraud signals from gate_results if available */}
                      {claim.fraud_signals && claim.fraud_signals.length > 0 && (
                        <div className="text-[10px] text-slate-600 mt-2 space-y-0.5">
                          {claim.fraud_signals.slice(0, 3).map((signal, j) => (
                            <div key={j} className="text-amber-700">🚩 {signal}</div>
                          ))}
                        </div>
                      )}
                      
                      {claim.detection_method && (
                        <p className="text-[10px] text-slate-400 mt-1">🔍 {claim.detection_method}</p>
                      )}
                      {claim.action_taken && (
                        <p className="text-[10px] text-green-600 mt-0.5 font-medium">
                          ✅ {claim.action_taken.substring(0, 80)}{claim.action_taken.length > 80 ? '...' : ''}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-500">No claims in review. Run a simulation or check Module 3.</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Model Info Section (Module 2) */}
      {modelInfo && (
        <Card className="border-t-4 border-t-blue-500">
          <CardHeader>
            <CardTitle>Model Metadata (Module 2)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              {modelInfo.model_name && (
                <div>
                  <p className="text-slate-500 uppercase font-semibold text-[10px] mb-1">Model</p>
                  <p className="text-slate-800 font-medium">{modelInfo.model_name}</p>
                </div>
              )}
              {modelInfo.version && (
                <div>
                  <p className="text-slate-500 uppercase font-semibold text-[10px] mb-1">Version</p>
                  <p className="text-slate-800 font-mono">{modelInfo.version}</p>
                </div>
              )}
              {modelInfo.accuracy && (
                <div>
                  <p className="text-slate-500 uppercase font-semibold text-[10px] mb-1">Accuracy</p>
                  <p className="text-slate-800 font-medium">{(modelInfo.accuracy * 100).toFixed(1)}%</p>
                </div>
              )}
            </div>
            {modelInfo.description && (
              <p className="text-xs text-slate-600 mt-3 leading-relaxed">{modelInfo.description}</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
