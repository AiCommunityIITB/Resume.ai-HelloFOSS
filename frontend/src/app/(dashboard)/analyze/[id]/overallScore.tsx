import { CheckCircle, TrendingUp } from "lucide-react";

const ScoreCard = ({ score, loading }: { score: number; loading: boolean }) => {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'from-green-500 to-emerald-400';
    if (score >= 60) return 'from-blue-500 to-cyan-400';
    if (score >= 40) return 'from-yellow-500 to-orange-400';
    return 'from-red-500 to-pink-400';
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 80) return 'bg-green-500/20 text-green-300 border-green-500/30';
    if (score >= 60) return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    if (score >= 40) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
    return 'bg-red-500/20 text-red-300 border-red-500/30';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Needs Improvement';
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/90 to-slate-700/90 rounded-2xl p-8 border border-slate-600/40 backdrop-blur-sm shadow-xl">
      {/* Header Section */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-start gap-4">
          <div className="relative">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
              <CheckCircle className="w-8 h-8 text-white" />
            </div>
            {!loading && (
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                <CheckCircle className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
          <div className="flex-1">
            <h3 className="text-2xl font-bold text-white mb-2">
              Overall Resume Score
            </h3>
            <p className="text-slate-300 leading-relaxed">
              Comprehensive evaluation across key areas including content quality, 
              formatting, keyword optimization, and overall effectiveness
            </p>
          </div>
        </div>

        {/* Score Display */}
        <div className="flex flex-col items-center gap-2">
          {loading ? (
            <div className="w-20 h-20 border-4 border-slate-600/30 border-t-blue-500 rounded-full animate-spin" />
          ) : (
            <>
              <div className="relative w-20 h-20">
                {/* Circular Progress */}
                <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-slate-700"
                    strokeDasharray="100, 100"
                    strokeWidth="3"
                    fill="none"
                    stroke="currentColor"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className={`text-blue-500 transition-all duration-1000 ease-out`}
                    strokeDasharray={`${score}, 100`}
                    strokeWidth="3"
                    strokeLinecap="round"
                    fill="none"
                    stroke="currentColor"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-white">{score}</span>
                </div>
              </div>
              <div className={`px-3 py-1 rounded-full border text-sm font-medium ${getScoreBadgeColor(score)}`}>
                {getScoreLabel(score)}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Performance Bar Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-lg font-semibold text-white mb-1">Performance Breakdown</h4>
            <p className="text-sm text-slate-400">Based on industry standards and best practices</p>
          </div>
          {/* <div className="text-right">
            <div className="text-2xl font-bold text-white">
              {loading ? "..." : `${score}/100`}
            </div>
            <div className="text-xs text-slate-400">Total Score</div>
          </div> */}
        </div>

        {/* Enhanced Progress Bar */}
        <div className="relative">
          <div className="w-full h-6 bg-slate-700/50 rounded-full overflow-hidden shadow-inner">
            <div
              className={`h-full bg-gradient-to-r ${getScoreColor(score)} transition-all duration-1000 ease-out relative rounded-full`}
              style={{
                width: loading ? "0%" : `${score}%`,
              }}
            >
              {!loading && (
                <div className="absolute inset-0 bg-white/20 rounded-full animate-pulse" />
              )}
            </div>
          </div>
          
          {/* Score Markers */}
          {!loading && (
            <div className="absolute top-8 left-0 right-0 flex justify-between text-xs text-slate-500">
              <span>0</span>
              <span>25</span>
              <span>50</span>
              <span>75</span>
              <span>100</span>
            </div>
          )}
        </div>

        {/* Score Insights */}
        {!loading && (
          <div className="mt-6 p-4 bg-slate-800/40 rounded-xl border border-slate-700/30">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center mt-1">
                <TrendingUp className="w-4 h-4 text-blue-400" />
              </div>
              <div className="flex-1">
                <h5 className="font-semibold text-white mb-1">Quick Insights</h5>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {score >= 80 ? "Outstanding! Your resume demonstrates excellent structure and content quality." :
                   score >= 60 ? "Good foundation! A few optimizations could enhance your resume's impact." :
                   score >= 40 ? "Solid start! Consider focusing on content refinement and keyword optimization." :
                   "Significant improvements needed. Focus on structure, content quality, and formatting."}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {/* {!loading && (
        <div className="mt-6 flex gap-3">
          <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors duration-200 font-medium text-sm">
            View Detailed Analysis
          </button>
          <button className="px-4 py-2 border border-slate-600/50 hover:bg-slate-800/50 text-slate-300 rounded-xl transition-colors duration-200 font-medium text-sm">
            Download Report
          </button>
        </div>
      )} */}
    </div>
  );
};

export default ScoreCard

