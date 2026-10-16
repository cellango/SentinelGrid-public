'use client'

import { Shield, TrendingUp, TrendingDown } from 'lucide-react'

interface ScoreCardProps {
  score: number;
  grade: string;
  trend?: number; // +5 or -3 etc
}

export function ScoreCard({ score, grade, trend }: ScoreCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-blue-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getGradeColor = (grade: string) => {
    if (grade === 'A') return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100';
    if (grade === 'B') return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100';
    if (grade === 'C') return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100';
    if (grade === 'D') return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100';
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100';
  };

  return (
    <div className="border rounded-lg p-6 bg-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <h2 className="text-lg font-semibold">Security Posture Score</h2>
        </div>
        
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {trend > 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
            <span>{trend > 0 ? '+' : ''}{trend}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-center gap-8">
        {/* Score */}
        <div className="text-center">
          <div className={`text-6xl font-bold ${getScoreColor(score)}`}>
            {score}
          </div>
          <div className="text-sm text-muted-foreground mt-1">
            out of 100
          </div>
        </div>

        {/* Grade */}
        <div className="text-center">
          <div className={`text-5xl font-bold px-6 py-3 rounded-lg ${getGradeColor(grade)}`}>
            {grade}
          </div>
          <div className="text-sm text-muted-foreground mt-1">
            Grade
          </div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t text-sm text-muted-foreground text-center">
        {score >= 90 && 'Excellent security posture! Keep it up.'}
        {score >= 75 && score < 90 && 'Good security posture. Address high findings to improve.'}
        {score >= 60 && score < 75 && 'Moderate security posture. Focus on critical and high findings.'}
        {score >= 40 && score < 60 && 'Concerning security posture. Immediate action recommended.'}
        {score < 40 && '⚠️ Critical security posture. Urgent action required.'}
      </div>
    </div>
  );
}

