"use client";

export default function KnowledgePage() {
  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Base de Conocimiento
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Gestiona documentos y FAQs para respuestas con IA
          </p>
        </div>
        <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700">
          Subir Documento
        </button>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            No hay documentos aún. Sube PDFs, archivos Word o páginas web para entrenar la IA.
          </p>
        </div>
      </div>
    </div>
  );
}
