import { Component, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { SearchService } from 'src/app/services/search.service';
import {ReplaySubject, takeUntil} from 'rxjs';
import { UserService } from 'src/app/services/user/user.service';
import { ActivatedRoute, Router } from '@angular/router';
import { search_document_type, search_image_type, PDF, image_name } from 'src/environments/constant';
import { DocumentService } from 'src/services/document.service';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss'],
})
export class SearchResultsComponent implements OnDestroy {
  @ViewChild('preview', { static: true })
  preview!: TemplateRef<{}>;
  summary: string = '';
  private readonly destroyed = new ReplaySubject<void>(1);
  serachResult : any = [];
  documents : any = [];
  images : any = [];
  pdf = PDF;
  imageName = image_name;
  documentURL: SafeResourceUrl;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private service : SearchService,
    private userService: UserService,
    private documentService: DocumentService,
    private sanitizer: DomSanitizer,
    private dialog : MatDialog,
  ){
    const query = this.route.snapshot.queryParamMap.get('q');

    this.service.search(query!).subscribe({
      next : (searchRespone: any)=>{
      this.serachResult = searchRespone;
      searchRespone.forEach((element: any) => {
        this.documents.push(element);
        if(search_image_type.includes(element.link.split(".")[1])){
          this.images.push(element);
        }
      });
      console.log(this.documents, this.images);
      this.userService.hideLoading();
      },
      error : ()=>{
        this.userService.hideLoading();
      }
    });
  }

  searchTerm(term: string) {
    this.router.navigate(['/search'], { queryParams: { q: term }});

    this.service.search(term).subscribe({
      next : (searchRespone: any)=>{
      this.serachResult = searchRespone;
      this.userService.hideLoading();
      },
      error : ()=>{
        this.userService.hideLoading();
      }
    });
  }

  openNewWindow(link: string) {
    window.open(link, "_blank")
  }

  previewDocument(data: any){
    this.documentService.getDocument(data.link).pipe(takeUntil(this.destroyed)).subscribe({
      next: (blob: Blob) => {
        const url = URL.createObjectURL(blob);
        this.documentURL = this.sanitizer.bypassSecurityTrustResourceUrl(url);
        this.dialog.open(this.preview, {data: data});
      },
      error : (error) => {
        console.error('Error loading Document:', error);
      }
    });
  }

  ngOnDestroy(){
    this.destroyed.next();
    this.destroyed.complete();
  }
}
