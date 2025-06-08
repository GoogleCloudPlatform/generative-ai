import React from "react";

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <p className="text-sm text-gray-500 text-center">
          Built by{" "}
          <a
            href="https://github.com/iprajwaal"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline"
          >
            iprajwaal
          </a>{" "}
          &copy; 2025
        </p>
      </div>
    </footer>
  );
}
