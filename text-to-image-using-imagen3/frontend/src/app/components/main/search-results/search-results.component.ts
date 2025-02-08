import { Component, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { SearchService } from 'src/app/services/search.service';
import {ReplaySubject, takeUntil} from 'rxjs';
import { UserService } from 'src/app/services/user/user.service';
import { ActivatedRoute, Router } from '@angular/router';
import { search_document_type, search_image_type, PDF, image_name } from 'src/environments/constant';
import { DomSanitizer, SafeResourceUrl, SafeUrl } from '@angular/platform-browser';
import { MatDialog } from '@angular/material/dialog';
import { GeneratedImage } from 'src/app/models/generated-image.model';

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
      next : (searchResponse: GeneratedImage[])=>{
    // const getImage = () => {
      //   [
      //     {
      //         "image": {
      //             "gcsUri": null,
      //             "imageBytes": "",
      //             "mimeType": "image/png"
      //         },
      //         "raiFilteredReason": null,
      //         "enhancedPrompt": null
      //     }
      // ]
      // const searchResponse: any = this.service.search(query!)
      console.log("[searchResponse]:", searchResponse)

      this.summary = searchResponse?.[0]?.enhancedPrompt || "";
      this.documents = searchResponse
      this.serachResult.forEach((element: GeneratedImage) => {
        // this.documents.push(element);
        this.images.push(element.image?.encodedImage);
      });

      // this.summary = searchResponse.summary;
      // this.serachResult = searchResponse.results;
      // this.serachResult.forEach((element: any) => {
      //   this.documents.push(element);
      //   if(search_image_type.includes(element.link.split(".")[1])){
      //     this.images.push(element);
      //   }
      // });
      // console.log(this.documents, this.images);
      this.userService.hideLoading();
      }
      ,
      error : ()=>{
        this.userService.hideLoading();
      }
    });
    // getImage()
  }

  getImage = (term: string) => {
    //   [
    //     {
    //         "image": {
    //             "gcsUri": null,
    //             "imageBytes": "",
    //             "mimeType": "image/png"
    //         },
    //         "raiFilteredReason": null,
    //         "enhancedPrompt": null
    //     }
    // ]
    const searchResponse: any = this.service.search(term)
    console.log("[searchResponse]:", searchResponse)

    this.summary = searchResponse?.[0]?.enhancedPrompt || "";
    this.documents = searchResponse
    this.serachResult.forEach((element: GeneratedImage) => {
      // this.documents.push(element);
      // const byteArray = element.image?.imageBytes
      // const base64_encoded_image = base64.b64encode(image_bytes).decode('utf-8')  # Important: decode to string

      this.images.push(element.image?.encodedImage);
    });

    // this.summary = searchResponse.summary;
    // this.serachResult = searchResponse.results;
    // this.serachResult.forEach((element: any) => {
    //   this.documents.push(element);
    //   if(search_image_type.includes(element.link.split(".")[1])){
    //     this.images.push(element);
    //   }
    // });
    // console.log(this.documents, this.images);
    this.userService.hideLoading();
    }

  searchTerm(term: string) {
    this.router.navigate(['/search'], { queryParams: { q: term }});
    // this.getImage(term)
    this.service.search(term).subscribe({
      next : (searchResponse: any)=>{
      this.serachResult = searchResponse.results;
      this.summary = searchResponse.summary;
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
    console.log("[pagedDocuments] documents:", this.documents)
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
