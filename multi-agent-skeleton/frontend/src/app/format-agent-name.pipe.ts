import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'formatAgentName'
})
export class FormatAgentNamePipe implements PipeTransform {

  transform(value: string | undefined | null, ...args: unknown[]): string {
    if (!value || typeof value !== 'string') {
      // Return a default or empty string if value is not as expected
      return 'Unknown Agent';
    }
    return value
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }
}
