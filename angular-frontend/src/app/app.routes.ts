import { Routes } from '@angular/router';
import { JobListComponent } from './components/job-list/job-list.component';

export const routes: Routes = [
    {path: '',component: JobListComponent},
    {path: '**',redirectTo: ''}
];
