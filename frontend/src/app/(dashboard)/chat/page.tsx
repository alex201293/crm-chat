"use client";

export default function ChatPage() {
  return (
    <div className="flex h-full">
      {/* Lista de conversaciones */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700">
        <div className="flex h-full flex-col">
          <div className="border-b border-gray-200 p-4 dark:border-gray-700">
            <input
              type="search"
              placeholder="Buscar conversaciones..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800"
              aria-label="Buscar conversaciones"
            />
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              No hay conversaciones aún. Los mensajes de WhatsApp y el widget aparecerán aquí.
            </p>
          </div>
        </div>
      </div>

      {/* Área de chat */}
      <div className="flex flex-1 items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">
          Selecciona una conversación para comenzar
        </p>
      </div>
    </div>
  );
}
