import { Component } from '@angular/core';
import { RouterLink } from "@angular/router";
import { SearchComponent } from "../search/search.component";

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, SearchComponent],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css'
})
export class NavbarComponent {

}
