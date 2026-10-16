export default function Footer() {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="border-t border-[rgba(15,23,42,0.9)] py-6 px-6 bg-[rgba(2,6,23,0.95)]">
      <div className="max-w-7xl mx-auto flex flex-wrap gap-3 items-center justify-between">
        <span className="font-semibold">
          Sentinel<span className="text-primary">Grid</span>
        </span>
        <span className="text-xs text-text-muted">
          © {currentYear} SentinelGrid. All rights reserved.
        </span>
        <div className="flex gap-4 text-xs">
          <a href="#resources" className="text-text-muted hover:text-primary">
            Resources
          </a>
          <a href="#contact" className="text-text-muted hover:text-primary">
            Contact
          </a>
          <a href="#" className="text-text-muted hover:text-primary">
            Privacy
          </a>
        </div>
      </div>
    </footer>
  );
}

