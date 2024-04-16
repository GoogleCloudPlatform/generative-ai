import "./Image.css";

export default function HomePage() {
  const imgText = "Hi, This is Kavach Insurance Company";

  return (
    <>
      <img className="image3" src={require("./home_page.png")} alt={imgText} />
    </>
  );
}
