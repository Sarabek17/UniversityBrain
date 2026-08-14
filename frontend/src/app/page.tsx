import uz from "@/i18n/uz.json";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-4xl font-bold">{uz.home.title}</h1>
      <p className="text-lg text-gray-600 dark:text-gray-300">
        {uz.home.subtitle}
      </p>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {uz.home.status}
      </p>
    </main>
  );
}
