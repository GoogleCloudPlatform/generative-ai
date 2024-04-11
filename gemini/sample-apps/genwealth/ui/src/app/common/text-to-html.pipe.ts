import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'textToHtml',
  standalone: true
})
export class TextToHtmlPipe implements PipeTransform {

  transform(value?: string): string {
    if (!value)
      return '';
    
    // Handle line breaks first
    value = value.replace(/\n/g, '<br />');

    // Handle bold formatting with regular expressions
    value = value.replace(/\*\*([^\*]+)\*\*/g, '<b>$1</b>');

    return value;
  }
}
