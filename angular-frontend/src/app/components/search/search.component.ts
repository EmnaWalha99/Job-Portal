import { Component ,signal, computed} from '@angular/core';
import {FormsModule} from '@angular/forms';
import { SearchService } from '../../services/search.service';
@Component({
  selector: 'app-search',
  standalone: true,
  imports: [FormsModule],
  template: `
      <input
        type="text"
        [(ngModel)]="searchTerm"
        placeholder="Rechercher par titre, mot-clé ou pays..."
        class="search-input"
      />
  `,
  styleUrl: './search.component.css'
})
export class SearchComponent {
  searchTerm='';
  constructor(private searchService: SearchService) {
    // Synchronise l'input avec le signal global
    this.searchTerm = this.searchService.searchTerm();
  }

  updateSearch(value: string) {
    this.searchTerm = value;
    this.searchService.searchTerm.set(value.trim().toLowerCase());
  }

}
