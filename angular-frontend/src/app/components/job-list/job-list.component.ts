import { Component, signal ,computed} from '@angular/core';
import { JobCardComponent } from '../job-card/job-card.component';
import { JobService } from '../../services/job.service';
import { SearchService } from '../../services/search.service';
@Component({
  selector: 'app-job-list',
  standalone: true,
  imports: [JobCardComponent],
  template: `
    <div class="container">
      <div class="results-header">
        <h2>{{ filteredJobs().length }} offre{{ filteredJobs().length > 1 ? 's' : '' }} trouvée{{ filteredJobs().length > 1 ? 's' : '' }}</h2>
      </div>

      <div class="job-grid">
        @for (job of filteredJobs(); track $index) {
        <app-job-card
          [job]="job"
        />
        }
      </div>

      @if (filteredJobs().length === 0) {}
      <p class="no-results">
        Aucune offre ne correspond à votre recherche.
      </p>
    </div>
  `,
  styleUrl: './job-list.component.css'
})
export class JobListComponent {
  searchTerm = signal('');
  constructor(public jobService: JobService, public searchService:SearchService){
    // exposition du signal pour le search component
    (this.jobService as any).searchTerm=this.searchTerm;
  }
  filteredJobs = computed(()=>{
    const term = this.searchService.searchTerm();
    const jobs = this.jobService.jobs();

    if(!term) return jobs ; 
    return jobs.filter(job =>{
      const searchable =`
      ${job.title || ''}
        ${job.company || ''}
        ${job.city || ''} ${job.region || ''} ${job.location || ''}
        ${job.sector || ''} ${job.contract_type || ''}
        ${job.skills || ''}
        ${job.skillsArray?.join(' ') || ''}
      `.toLowerCase();
      return searchable.includes(term);
    });
  });

}
