import { Routes } from '@angular/router';
import { InvestmentsComponent } from './investments/investments.component';
import { ProspectsComponent } from './prospects/prospects.component';
import { ChatComponent } from './chat/chat.component';
import { ResearchComponent } from './research/research.component';

export const routes: Routes = [
    {path: 'investments', component: InvestmentsComponent},
    {path: 'research', component: ResearchComponent},
    {path: 'prospects', component: ProspectsComponent},
    {path: 'chat', component: ChatComponent},
    {path: 'chat/:userId', component: ChatComponent},
    {path: '', redirectTo: '/investments', pathMatch: 'full'},
];
