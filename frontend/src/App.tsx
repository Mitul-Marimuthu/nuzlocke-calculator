import { useState } from "react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import FileUpload from "./components/FileUpload";
import PartyDisplay from "./components/PartyDisplay";
import TrainerDisplay from "./components/TrainerDisplay";
import StrategyDisplay from "./components/StrategyDisplay";
import { createSession, uploadSav, uploadGba, analyze } from "./api";
import type { DisplayData, UploadStep } from "./types";

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [step, setStep] = useState<UploadStep>("idle");
  const [savDone, setSavDone] = useState(false);
  const [gbaDone, setGbaDone] = useState(false);
  const [trainerHint, setTrainerHint] = useState("");
  const [displayData, setDisplayData] = useState<DisplayData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ensureSession = async (): Promise<string> => {
    if (sessionId) return sessionId;
    const id = await createSession();
    setSessionId(id);
    return id;
  };

  const handleSav = async (file: File) => {
    setError(null);
    setStep("uploading_sav");
    try {
      const id = await ensureSession();
      await uploadSav(id, file);
      setSavDone(true);
      setStep("idle");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? e.message ?? "Failed to upload .sav");
      setStep("error");
    }
  };

  const handleGba = async (file: File) => {
    setError(null);
    setStep("uploading_gba");
    try {
      const id = await ensureSession();
      await uploadGba(id, file, trainerHint || undefined);
      setGbaDone(true);
      setStep("idle");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? e.message ?? "Failed to upload .gba");
      setStep("error");
    }
  };

  const handleAnalyze = async () => {
    if (!sessionId || !savDone || !gbaDone) return;
    setError(null);
    setStep("analyzing");
    try {
      const data = await analyze(sessionId);
      setDisplayData(data);
      setStep("done");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? e.message ?? "Analysis failed");
      setStep("error");
    }
  };

  const handleReset = () => {
    setSessionId(null);
    setStep("idle");
    setSavDone(false);
    setGbaDone(false);
    setTrainerHint("");
    setDisplayData(null);
    setError(null);
  };

  const isLoading = step === "uploading_sav" || step === "uploading_gba" || step === "analyzing";

  return (
    <div className="min-h-screen bg-pokenavy">
      {/* Header */}
      <header className="border-b border-pokeborder py-4 px-6 flex items-center justify-between">
        <div>
          <h1 className="font-pixel text-pokered text-base tracking-wide">NUZZY</h1>
          <p className="text-[10px] text-gray-500 font-pixel mt-0.5">Nuzlocke Battle Advisor</p>
        </div>
        {(savDone || gbaDone || displayData) && (
          <button onClick={handleReset} className="btn-secondary flex items-center gap-1.5 text-sm">
            <RefreshCw className="w-4 h-4" /> New Run
          </button>
        )}
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">

        {/* Upload section */}
        {!displayData && (
          <section className="space-y-6">
            <p className="font-pixel text-[11px] text-gray-400 text-center">
              Upload your save + ROM to get a no-item battle strategy
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
              <FileUpload
                label="Upload Save File (.sav)"
                accept=".sav"
                onFile={handleSav}
                disabled={isLoading}
                done={savDone}
                hint="Your Pokémon Emerald save"
              />
              <FileUpload
                label="Upload ROM File (.gba)"
                accept=".gba"
                onFile={handleGba}
                disabled={isLoading}
                done={gbaDone}
                hint="Your Pokémon Emerald ROM"
              />
            </div>

            {/* Trainer hint input */}
            {gbaDone === false && (
              <div className="max-w-xs mx-auto">
                <label className="block text-[10px] font-pixel text-gray-500 mb-1">
                  Next trainer name or index (optional)
                </label>
                <input
                  type="text"
                  value={trainerHint}
                  onChange={(e) => setTrainerHint(e.target.value)}
                  placeholder='e.g. "Roxanne" or "48"'
                  disabled={isLoading}
                  className="w-full bg-pokecard border border-pokeborder rounded-lg px-3 py-2
                             text-sm text-gray-200 placeholder-gray-600
                             focus:outline-none focus:border-pokered transition-colors"
                />
              </div>
            )}

            {/* Analyze button */}
            <div className="text-center">
              <button
                className="btn-primary min-w-[200px] flex items-center justify-center gap-2 mx-auto"
                onClick={handleAnalyze}
                disabled={!savDone || !gbaDone || isLoading}
              >
                {step === "analyzing" ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  "Analyze Battle"
                )}
              </button>
              {isLoading && step !== "analyzing" && (
                <p className="text-[10px] text-gray-500 mt-2 flex items-center justify-center gap-1.5">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {step === "uploading_sav" ? "Parsing save file..." : "Parsing ROM..."}
                </p>
              )}
            </div>
          </section>
        )}

        {/* Error */}
        {error && (
          <div className="max-w-2xl mx-auto card border border-red-700 bg-red-900/20 flex gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-pixel text-[10px] text-red-400 mb-0.5">Error</p>
              <p className="text-sm text-red-300">{error}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {displayData && (
          <div className="space-y-8">
            {/* Strategy banner */}
            <div className="card border border-pokegold/40 bg-pokegold/5 text-center">
              <p className="font-pixel text-pokegold text-xs">Analysis Complete</p>
              <p className="text-gray-400 text-sm mt-1">
                {displayData.player.trainer_name} vs{" "}
                {displayData.opponent.trainer_class} {displayData.opponent.name}
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left: Player Party */}
              <div className="lg:col-span-1">
                <PartyDisplay
                  data={displayData.player}
                  leadName={displayData.strategy.lead_recommendation}
                />
              </div>

              {/* Center: Strategy */}
              <div className="lg:col-span-1">
                <StrategyDisplay strategy={displayData.strategy} />
              </div>

              {/* Right: Opponent */}
              <div className="lg:col-span-1">
                <TrainerDisplay data={displayData.opponent} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
