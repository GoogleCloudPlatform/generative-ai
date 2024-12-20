import { Component, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { SearchService } from 'src/app/services/search.service';
import {ReplaySubject, takeUntil} from 'rxjs';
import { UserService } from 'src/app/services/user/user.service';
import { ActivatedRoute, Router } from '@angular/router';
import { search_document_type, search_image_type, PDF, image_name } from 'src/environments/constant';
import { DomSanitizer, SafeResourceUrl, SafeUrl } from '@angular/platform-browser';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss'],
})
export class SearchResultsComponent implements OnDestroy {
  @ViewChild('preview', { static: true })
  previewRef!: TemplateRef<{}>;
  summary: string = '';
  private readonly destroyed = new ReplaySubject<void>(1);
  serachResult : any = [];
  documents : any = [];
  images : any = [];
  pdf = PDF;
  imageName = image_name;
  documentURL: SafeResourceUrl;
  openPreviewDocument: any;
  currentPage = 0;
  pageSize = 3;
  selectedDocument: any;
  safeUrl: SafeUrl;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private service : SearchService,
    private userService: UserService,
    private dialog : MatDialog,
    private sanitizer: DomSanitizer,
  ){
    const query = this.route.snapshot.queryParamMap.get('q');

    this.service.search(query!).subscribe({
      next : (searchRespone: any)=>{
      this.summary = searchRespone.summary;
      this.serachResult = searchRespone.results;
      this.serachResult.forEach((element: any) => {
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
      this.serachResult = searchRespone.results;
      this.summary = searchRespone.summary;
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

  previewDocument(event: any, document: any){
    event.stopPropagation();
    if(document.link.endsWith(".pdf") || document.link.endsWith(".docx")) {
      this.selectedDocument = document;
      this.safeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.selectedDocument.link);
    }
  }

  closePreview() {
    this.selectedDocument = undefined;
  }

  ngOnDestroy(){
    this.destroyed.next();
    this.destroyed.complete();
  }

  get pagedDocuments() {
    const startIndex = this.currentPage * this.pageSize;
    return this.documents.slice(startIndex, startIndex + this.pageSize);
  }

  get totalPages() {
    return Math.ceil(this.documents.length / this.pageSize);
  }

  nextPage() {
    if (this.currentPage < this.totalPages - 1) {
      this.currentPage++;
    }
  }

  prevPage() {
    if (this.currentPage > 0) {
      this.currentPage--;
    }
  }

}
