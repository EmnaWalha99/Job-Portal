import { Component, input } from '@angular/core';
import { Job, parseSkills } from '../../models/job.model';
import { DatePipe, CurrencyPipe } from '@angular/common';

@Component({
  selector: 'app-job-card',
  standalone: true,
  imports: [DatePipe, CurrencyPipe],
  template: `
    <article class="job-card">
      <div class="header">
        <h3 class="title">{{ job().title || 'Offre sans titre' }}</h3>
        <p class="company">{{ job().company || 'Entreprise non précisée' }}</p>
      </div>

      <div class="location">
        <strong>Location:</strong> {{ job().city || job().region || job().location || 'Non précisé' }}
      </div>

      <div class="details">
        @if (job().contract_type) {
        <span class="badge">{{ job().contract_type }}</span>
        }
        @if (job().sector) {
        <span class="badge">{{ job().sector }}</span>
        }
        
        @if (job().experience) {
        <span class="badge">{{ job().experience }}</span>
        }
      </div>
      
      @if (job().skillsArray.length) {
      <div class="skills">
        @for (skill of job().skillsArray; track $index) {
        <span class="skill-tag">{{ skill }}</span>
        }
      </div>
      }
      
      @if (hasSalary()) {
      <div class="salary">
        <strong>Salaire :</strong>
        {{ formatSalary() }}
      </div>
      }
      <div class="footer">
        <small>
          Publié le {{ job().date_publication | date:'shortDate' }}
          • Source : {{ job().source }}
        </small>
      </div>

      <a [href]="job().detail_link" target="_blank" class="btn-primary" rel="noopener">
        Voir l'offre originale
      </a>
    </article>
  `,
  styleUrls: ['./job-card.component.css']
})
export class JobCardComponent {
  job = input.required<Job & { skillsArray: string[] }>();

  hasSalary() {
    return this.job().salary_min || this.job().salary_max;
  }

  formatSalary() {
    const { salary_min, salary_max } = this.job();
    if (salary_min && salary_max) {
      return `${salary_min.toLocaleString()} € - ${salary_max.toLocaleString()} €`;
    }
    if (salary_min) return `À partir de ${salary_min.toLocaleString()} €`;
    if (salary_max) return `Jusqu'à ${salary_max.toLocaleString()} €`;
    return 'Salaire non communiqué';
  }
}