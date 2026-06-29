import Link from 'next/link';
import styles from './LandingFooter.module.css';

export default function LandingFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.centerWrap}>
        {/* Scattered particles behind the logo */}
        <div className={styles.particles}>
          <span className={`${styles.particle} ${styles.p1}`} />
          <span className={`${styles.particle} ${styles.p2}`} />
          <span className={`${styles.particle} ${styles.p3}`} />
          <span className={`${styles.particle} ${styles.p4}`} />
          <span className={`${styles.particle} ${styles.p5}`} />
          <span className={`${styles.particle} ${styles.p6}`} />
          <span className={`${styles.particle} ${styles.p7}`} />
          <span className={`${styles.particle} ${styles.p8}`} />
        </div>

        <div className={styles.logoContainer}>
          <h1 className={styles.logo}>SAMAS</h1>
          <div className={styles.mirrorLine} />
          <h1 className={styles.logoMirrored}>SAMAS</h1>
        </div>

        <p className={styles.manifesto}>Your reflection, verified.</p>
      </div>
      
      <div className={styles.bottomBar}>
        <div className={styles.credit}>
          ARCHITECTED BY <a href="https://www.linkedin.com/in/shivam-rajput-3928a328a/" target="_blank" rel="noopener noreferrer" className={styles.creditLink}>SHIVAM</a>
        </div>
        <div className={styles.links}>
          <Link href="/find" className={styles.link}>ENTER SYSTEM</Link>
        </div>
      </div>
    </footer>
  );
}
