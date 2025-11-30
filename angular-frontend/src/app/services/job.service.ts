import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Job, parseSkills } from '../models/job.model';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { Observable } from 'rxjs';

export type JobWithSkills = Job & { skillsArray: string[] };
@Injectable({ providedIn: 'root' })
export class JobService {
  //Données statiques pour tester
  private mockJobs: (Job & { skillsArray: string[] })[] = [
    {
      id: 1,
      job_id: "123456",
      source: "France Travail",
      title: "Développeur Full Stack Angular / Node.js (H/F)",
      detail_link: "https://candidat.francetravail.fr/offres/emploi/developpeur-full-stack/s123456",
      company: "TechNova",
      date_publication: "2025-11-28",
      sector: "Informatique",
      contract_type: "CDI",
      study_level: "Bac +5",
      experience: "3 à 5 ans",
      availability: "Dès que possible",
      location: "Lyon",
      city: "Lyon",
      region: "Auvergne-Rhône-Alpes",
      salary_min: 42000,
      salary_max: 55000,
      description: "Rejoignez notre équipe dynamique...",
      skills: "Angular, TypeScript, Node.js, Docker, Git, MongoDB, REST API",
      scraped_at: "2025-11-29T10:30:00Z",
      skillsArray: [] // sera rempli ci-dessous
    },
    {
      id: 2,
      job_id: "789012",
      source: "Indeed",
      title: "Data Engineer Senior",
      detail_link: "https://fr.indeed.com/voir-emploi?id=789012",
      company: "DataPulse",
      date_publication: "2025-11-25",
      sector: "Data",
      contract_type: "CDI",
      study_level: "Bac +5",
      experience: "5 ans et plus",
      city: "Paris",
      region: "Île-de-France",
      salary_min: 60000,
      salary_max: 75000,
      skills: "Python, Spark, AWS, SQL, Airflow, Databricks",
      scraped_at: "2025-11-29T08:15:00Z",
      skillsArray: []
    }
  ].map(job => ({
    ...job,
    skillsArray: parseSkills(job.skills)
  }));

  // Signal avec les données mockées (triées par date décroissante)
  jobs = signal<(Job & { skillsArray: string[] })[]>(
    this.mockJobs.sort((a, b) => 
      new Date(b.date_publication || 0).getTime() - new Date(a.date_publication || 0).getTime()
    )
  );

  // Optionnel : méthode pour recharger ou simuler un refresh
  refresh() {
    this.jobs.set([...this.mockJobs]); // force un update du signal
  }
  

  

}