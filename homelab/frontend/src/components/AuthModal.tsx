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
    }, 450);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md glass-card border border-white/15 rounded-3xl shadow-2xl p-6 relative overflow-hidden">
        {/* Ambient Top Glow */}
        <div className="absolute -top-12 -left-12 w-32 h-32 bg-noop-cyan/15 rounded-full blur-2xl pointer-events-none" />

        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-noop-subtle hover:text-white p-2 rounded-xl hover:bg-white/5 active:scale-90 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3.5 mb-4">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-noop-cyan/25 to-noop-cyan/5 border border-noop-cyan/30 flex items-center justify-center text-noop-cyan shadow-glowCyan">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-extrabold text-white tracking-tight">Dashboard Authentication</h3>
            <p className="text-xs text-noop-subtle font-medium">Enter your Bearer session token</p>
          </div>
        </div>

        <p className="text-xs text-noop-muted mb-4 leading-relaxed">
          The dashboard communicates directly with your Home Lab FastAPI backend over your private Tailscale WireGuard mesh.
          The token is kept securely in your browser's local storage and is never transmitted off-device.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-noop-muted uppercase tracking-wider mb-2">
              Bearer Session Token
            </label>
            <div className="relative">
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste your DASHBOARD_TOKEN"
                className="w-full bg-noop-bg/90 border border-white/10 focus:border-noop-cyan rounded-xl px-4 py-3 text-sm text-white placeholder-noop-subtle outline-none transition-all shadow-inner font-mono"
                required
              />
              <Key className="w-4 h-4 text-noop-subtle absolute right-3.5 top-3.5" />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-noop-subtle">
              Default: <code className="bg-white/5 px-2 py-0.5 rounded text-noop-cyan font-mono text-[10px]">changeme_dashboard...</code>
            </span>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl bg-noop-cyan hover:bg-noop-cyan/90 active:scale-95 text-black font-extrabold text-xs tracking-wide transition-all flex items-center gap-2 shadow-glowCyan"
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
