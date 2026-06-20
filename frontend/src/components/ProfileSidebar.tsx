'use client';
/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import styles from './ProfileSidebar.module.css';

interface Props {
  profile: any;
}

export default function ProfileSidebar({ profile }: Props) {
  if (!profile) return null;

  return (
    <aside className={styles.sidebar}>
      <h3 className={styles.header}>Extracted Profile</h3>

      <div className={styles.section}>
        <div className={styles.name}>{profile.personal_info?.full_name || 'Candidate'}</div>
        <div className={styles.subtext}>{profile.personal_info?.email}</div>
      </div>

      <div className={styles.section}>
        <h4 className={styles.subHeader}>Top Skills Verified</h4>
        <div className={styles.skillList}>
          {profile.skills?.slice(0, 10).map((skill: any, index: number) => (
            <span key={index} className={styles.skillTag}>
              {skill.name}{' '}
              <span className={styles.skillLevel}>
                {Math.round((skill.proof_score || 0) * 100)}%
              </span>
            </span>
          ))}
          {profile.skills?.length > 10 && (
            <span className={styles.skillTag}>+{profile.skills.length - 10} more</span>
          )}
        </div>
      </div>

      <div className={styles.section}>
        <h4 className={styles.subHeader}>Experience Level</h4>
        <div className={styles.expBox}>
          {profile.work_experience?.length || 0} Roles Found
        </div>
      </div>
    </aside>
  );
}
