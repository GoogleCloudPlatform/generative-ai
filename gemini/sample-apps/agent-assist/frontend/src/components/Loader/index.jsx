import "./loader.css";

export default function Loader(props) {
  // Destructure the children prop from the props object
  const { children } = props;
  // Return a div containing the children, and two loader divs with classes loader1 and loader2
  return (
    <div>
      {children}
      <div className="loader loader1"></div>
      <div className="loader loader2"></div>
    </div>
  );
}
