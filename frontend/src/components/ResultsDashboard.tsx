'use client';
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import styles from './ResultsDashboard.module.css';

interface MatchedJob {
  job: {
    id: string;
    title: string;
    company: string;
    location: string;
    url: string;
    source: string;
  };
  jd_requirements: {
    ghost_probability: number;
    ghost_reasoning: string;
  };
  match_score: number;
  tier: 'easy_get' | 'best_match' | 'stretch_goal' | 'filtered' | 'ghost';
  skill_gap_summary: string;
  matched_skills: string[];
  missing_skills: string[];
}

interface Props {
  jobs: MatchedJob[];
  droppedJobs?: any[];
  profile: any;
}

export default function ResultsDashboard({ jobs, droppedJobs = [], profile }: Props) {
  const [activeTier, setActiveTier] = useState<string>('best_match');
  const [hideGhostJobs, setHideGhostJobs] = useState(false);
  const [locationFilter, setLocationFilter] = useState('');

  const applyFilters = (jobLike: MatchedJob | any, isDropped: boolean) => {
    if (hideGhostJobs && !isDropped && jobLike.jd_requirements?.ghost_probability > 0.2) {
      return false;
    }

    const jobData = isDropped ? jobLike : jobLike.job;
    if (locationFilter) {
      if (!jobData?.location) return false;
      if (!jobData.location.toLowerCase().includes(locationFilter.toLowerCase())) {
        return false;
      }
    }

    return true;
  };

  const filteredJobs = activeTier === 'dropped'
    ? droppedJobs.filter((job) => applyFilters(job, true))
    : jobs.filter((job) => job.tier === activeTier && applyFilters(job, false));

  const counts = {
    easy_get: jobs.filter((job) => job.tier === 'easy_get').length,
    best_match: jobs.filter((job) => job.tier === 'best_match').length,
    stretch_goal: jobs.filter((job) => job.tier === 'stretch_goal').length,
    dropped: droppedJobs.length,
  };

  return (
    <div className={styles.dashboard}>
      <div className={styles.statsRow}>
        <div className={`glass-panel ${styles.statCard}`}>
          <h3>{profile?.personal_info?.full_name || 'Profile'}</h3>
          <p className={styles.statValue}>{profile?.skills?.length || 0}</p>
          <p className={styles.statLabel}>Verified Skills</p>
        </div>
        <div className={`glass-panel ${styles.statCard}`}>
          <h3>Total Matches</h3>
          <p className={styles.statValue}>{jobs.length}</p>
          <p className={styles.statLabel}>Deduplicated and Analyzed</p>
        </div>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTier === 'best_match' ? styles.activeTab : ''}`}
          onClick={() => setActiveTier('best_match')}
        >
          Best Match ({counts.best_match})
        </button>
        <button
          className={`${styles.tab} ${activeTier === 'easy_get' ? styles.activeTab : ''}`}
          onClick={() => setActiveTier('easy_get')}
        >
          Easy Get ({counts.easy_get})
        </button>
        <button
          className={`${styles.tab} ${activeTier === 'stretch_goal' ? styles.activeTab : ''}`}
          onClick={() => setActiveTier('stretch_goal')}
        >
          Stretch Goal ({counts.stretch_goal})
        </button>
        {counts.dropped > 0 && (
          <button
            className={`${styles.tab} ${activeTier === 'dropped' ? styles.activeTab : ''}`}
            onClick={() => setActiveTier('dropped')}
          >
            Dropped by AI ({counts.dropped})
          </button>
        )}
      </div>

      <div className={styles.filtersBar}>
        <input
          type="text"
          placeholder="Filter by location"
          className="input-glass"
          value={locationFilter}
          onChange={(event) => setLocationFilter(event.target.value)}
        />
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={hideGhostJobs}
            onChange={(event) => setHideGhostJobs(event.target.checked)}
          />
          Hide ghost jobs above 20% risk
        </label>
      </div>

      <div className={styles.jobList}>
        {filteredJobs.length === 0 ? (
          <div className={styles.emptyState}>No jobs found in this tier.</div>
        ) : (
          filteredJobs.map((match, index) => {
            const isDropped = activeTier === 'dropped';
            const jobData = isDropped ? match : match.job;
            const dropReason = isDropped ? (match.metadata?.drop_reason || 'Low relevance') : '';

            return (
              <div key={`${jobData?.id || jobData?.title || 'job'}-${index}`} className={`glass-panel ${styles.jobCard}`}>
                <div className={styles.jobHeader}>
                  <div>
                    <h3 className={styles.jobTitle}>{jobData.title}</h3>
                    <p className={styles.jobCompany}>{jobData.company} - {jobData.location}</p>
                  </div>
                  {!isDropped && match.match_score !== undefined && (
                    <div className={styles.scoreCircle}>
                      <svg viewBox="0 0 36 36" className={styles.circularChart}>
                        <path
                          className={styles.circleBg}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                        <path
                          className={styles.circle}
                          strokeDasharray={`${match.match_score * 100}, 100`}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                        <text x="18" y="20.35" className={styles.percentage}>
                          {(match.match_score * 100).toFixed(0)}%
                        </text>
                      </svg>
                    </div>
                  )}
                </div>

                {!isDropped && match.jd_requirements?.ghost_probability > 0.2 && (
                  <div className={styles.ghostWarning}>
                    <strong>Ghost Job Risk: {(match.jd_requirements.ghost_probability * 100).toFixed(0)}%</strong>
                    <p>{match.jd_requirements.ghost_reasoning}</p>
                  </div>
                )}

                {isDropped ? (
                  <div className={styles.gapAnalysis}>
                    <h4>Drop Reason</h4>
                    <p className={styles.gapSummary} style={{ color: 'var(--accent-rose)' }}>{dropReason}</p>
                  </div>
                ) : (
                  <div className={styles.gapAnalysis}>
                    <h4>Gap Analysis</h4>
                    <p className={styles.gapSummary}>{match.skill_gap_summary}</p>

                    <div className={styles.skillsLists}>
                      <div className={styles.skillBox}>
                        <span className={styles.skillIcon}>+</span>
                        <div className={styles.skillTags}>
                          {match.matched_skills?.map((skill: string) => (
                            <span key={skill} className={styles.tagMatched}>{skill}</span>
                          ))}
                          {(!match.matched_skills || match.matched_skills.length === 0) && (
                            <span className={styles.tagNone}>None</span>
                          )}
                        </div>
                      </div>
                      <div className={styles.skillBox}>
                        <span className={styles.skillIcon}>-</span>
                        <div className={styles.skillTags}>
                          {match.missing_skills?.map((skill: string) => (
                            <span key={skill} className={styles.tagMissing}>{skill}</span>
                          ))}
                          {(!match.missing_skills || match.missing_skills.length === 0) && (
                            <span className={styles.tagNone}>None</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className={styles.jobFooter}>
                  <a href={jobData.url} target="_blank" rel="noreferrer" className={`btn-primary ${styles.applyBtn}`}>
                    APPLY
                  </a>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
