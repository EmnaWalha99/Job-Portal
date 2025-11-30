import { Injectable, signal, WritableSignal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class SearchService {
  // Signal public réactif pour la recherche
  searchTerm: WritableSignal<string> = signal('');
}