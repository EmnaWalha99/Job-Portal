export interface Job {
  id: number;
  job_id: string;
  source: string;
  title?: string;
  detail_link?: string;
  company?: string;
  date_publication?: string;
  sector?: string;
  contract_type?: string;
  study_level?: string;
  experience?: string;
  availability?: string;
  location?: string;
  region?: string;
  city?: string;
  salary_min?: number;
  salary_max?: number;
  description?: string;
  skills?: string;
  scraped_at?: string; // ISO string
}

// Utilitaire pour transformer les skills string → array
export const parseSkills = (skills?: string): string[] => {
  if (!skills) return [];
  return skills.split(',').map(s => s.trim()).filter(Boolean);
};
