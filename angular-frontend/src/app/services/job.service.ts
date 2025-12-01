import { Injectable, signal, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Job, parseSkills } from '../models/job.model';
import { toSignal } from '@angular/core/rxjs-interop';
import { map, catchError, of } from 'rxjs';
import { Observable } from 'rxjs';

export type JobWithSkills = Job & { skillsArray: string[] };

interface JobsResponse {
  jobs: Job[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class JobService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/jobs'; // Ajustez selon votre config

  // Signal pour stocker les jobs
  jobs = signal<JobWithSkills[]>([]);
  
  // Signal pour le loading state
  loading = signal<boolean>(false);
  
  // Signal pour les erreurs
  error = signal<string | null>(null);

  constructor() {
    // Chargement initial des jobs
    this.loadJobs();
  }

  /**
   * Charge les jobs depuis l'API
   */
  loadJobs(params?: {
    search?: string;
    country?: string;
    limit?: number;
    offset?: number;
  }) {
    this.loading.set(true);
    this.error.set(null);

    let httpParams = new HttpParams();
    
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.country) {
      httpParams = httpParams.set('country', params.country);
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    this.http.get<Job[]>(this.apiUrl, { params: httpParams }).pipe(
      map(jobs => {
        console.log('[DEBUG] Jobs reçus:', jobs.length);
        return jobs.map(job => ({
          ...job,
          skillsArray: parseSkills(job.skills)
        }));
      }),
      catchError(err => {
        console.error('Erreur lors du chargement des jobs:', err);
        this.error.set('Impossible de charger les offres d\'emploi');
        return of([]);
      })
    ).subscribe(jobsWithSkills => {
      console.log('[DEBUG] Jobs avec skills:', jobsWithSkills.length);
      this.jobs.set(jobsWithSkills);
      this.loading.set(false);
    });
  }

  /**
   * Recherche des jobs avec des filtres
   */
  searchJobs(searchTerm: string, country?: string) {
    this.loadJobs({ search: searchTerm, country, limit: 50, offset: 0 });
  }

  /**
   * Rafraîchit la liste des jobs
   */
  refresh() {
    this.loadJobs();
  }

  /**
   * Retourne un Observable pour une utilisation avec toSignal
   */
  getJobs$(params?: {
    search?: string;
    country?: string;
    limit?: number;
    offset?: number;
  }): Observable<JobWithSkills[]> {
    let httpParams = new HttpParams();
    
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.country) {
      httpParams = httpParams.set('country', params.country);
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<Job[]>(this.apiUrl, { params: httpParams }).pipe(
      map(jobs => jobs.map(job => ({
        ...job,
        skillsArray: parseSkills(job.skills)
      }))),
      catchError(err => {
        console.error('Erreur lors du chargement des jobs:', err);
        return of([]);
      })
    );
  }

  /**
   * Récupère un job par son ID
   */
  getJobById(id: number): Observable<JobWithSkills | null> {
    return this.http.get<Job>(`${this.apiUrl}/${id}`).pipe(
      map(job => ({
        ...job,
        skillsArray: parseSkills(job.skills)
      })),
      catchError(err => {
        console.error('Erreur lors du chargement du job:', err);
        return of(null);
      })
    );
  }
}