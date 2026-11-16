import React, { useState } from "react";
import { Key, Lock, ShieldCheck, X } from "lucide-react";
import { getDashboardToken, setDashboardToken } from "../api/client";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSaved }) => {
  const [token, setToken] = useState(getDashboardToken());
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setDashboardToken(token);
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onSaved();
      onClose();
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-noop-card border border-noop-border rounded-2xl shadow-2xl p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-noop-subtle hover:text-white p-1 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-noop-cyan/10 border border-noop-cyan/20 flex items-center justify-center text-noop-cyan">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Dashboard Authentication</h3>
            <p className="text-xs text-noop-subtle">Enter your Bearer session token</p>
          </div>
        </div>

        <p className="text-xs text-noop-muted mb-4 leading-relaxed">
          The dashboard communicates directly with your Home Lab FastAPI backend over Tailscale.
          The token is kept securely in your browser's local storage and is never sent off-device.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-noop-muted uppercase tracking-wider mb-1.5">
              Bearer Session Token
            </label>
            <div className="relative">
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste your DASHBOARD_TOKEN"
                className="w-full bg-noop-bg border border-noop-border focus:border-noop-cyan rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-noop-subtle outline-none transition-colors"
                required
              />
              <Key className="w-4 h-4 text-noop-subtle absolute right-3.5 top-3" />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-noop-subtle">
              Default: <code className="bg-noop-bg px-1.5 py-0.5 rounded text-noop-cyan">changeme_dashboard_session_token</code>
            </span>
            <button
              type="submit"
              className="px-4 py-2 rounded-xl bg-noop-cyan hover:bg-noop-cyan/90 text-black font-semibold text-xs tracking-wide transition-colors flex items-center gap-1.5"
            >
              {savedSuccess ? (
                <>
                  <ShieldCheck className="w-4 h-4 text-black" />
                  Saved!
                </>
              ) : (
                "Save & Connect"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
