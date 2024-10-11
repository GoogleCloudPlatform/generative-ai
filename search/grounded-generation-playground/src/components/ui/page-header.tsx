import React from 'react';
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';
import { Helmet } from 'react-helmet';

interface PageHeaderProps {
  toggleSidebar: () => void;
}

const PageHeader: React.FC<PageHeaderProps> = ({ toggleSidebar }) => {
  return (
    <>
      <Helmet>
        <style>
          {`
            @import url('https://fonts.googleapis.com/css2?family=Google+Sans:ital,opsz,wght@0,17..18,400..700;1,17..18,400..700&display=swap');

            .google-sans-header {
              font-family: "Google Sans", sans-serif;
              font-optical-sizing: auto;
              font-weight: 500;
              font-style: normal;
              font-variation-settings: "GRAD" 0;
            }
          `}
        </style>
      </Helmet>
      <header className="bg-zinc-900 shadow-md border-b border-zinc-800">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1
              className="text-2xl google-sans-header text-transparent bg-clip-text"
              style={{
                backgroundImage: 'linear-gradient(72.83deg, #4285F4 11.63%, #9b72cb 40.43%, #d96570 68.07%)',
              }}
            >
              Vertex AI Search Grounded Generation Playground
            </h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="lg:hidden text-white"
            >
              <Menu className="h-6 w-6" />
            </Button>
          </div>
        </div>
      </header>
    </>
  );
};

export default PageHeader;