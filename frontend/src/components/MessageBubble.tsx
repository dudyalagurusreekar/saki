export default function MessageBubble({ role, text }: any) {
  return (
    <div className={`p-3 rounded-lg max-w-xl ${
      role === "user" ? "bg-blue-500 ml-auto" : "bg-gray-700"
    }`}>
      {text}
    </div>
  );
}
