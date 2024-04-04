import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';

@Component({
  selector: 'app-sql-statement',
  standalone: true,
  imports: [
    CommonModule,
    MatExpansionModule,
  ],
  templateUrl: './sql-statement.component.html',
  styleUrl: './sql-statement.component.scss'
})
export class SqlStatementComponent {
  @Input()
  query?: string = undefined;
}
