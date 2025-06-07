import React from "react";

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <p className="text-sm text-gray-500 text-center">
          &copy; {new Date().getFullYear()} AI Market Analyst. All rights
          reserved.
        </p>
      </div>
    </footer>
  );
}
