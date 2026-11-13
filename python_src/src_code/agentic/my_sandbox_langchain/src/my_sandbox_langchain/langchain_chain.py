import random
from typing import ClassVar

from langchain_core.messages.ai import AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from other_tools.profilers import pyinstrument_prof_decorator, yappi_prof_decor
from pydantic import SecretStr


def _create_llm() -> ChatOpenAI:
    """Создаёт и возвращает экземпляр LLM с настройками по умолчанию."""
    return ChatOpenAI(
        model="Kestrel-4B-Coder",
        base_url="http://127.0.0.1:9932",
        api_key=SecretStr("no-key-needed"),
        temperature=0,
    )


class TestLLMInfo:
    """Реализация протокола выдачи сообщений.

    В __data заранее собирается несколько случайных наборов
    (system, human) промптов; get_prompt_set возвращает случайный из них.
    """

    SYSTEM_ROLES: ClassVar[tuple[str, ...]] = (
        "эксперт по данным",
        "внимательный рецензент",
        "технический писатель",
        "аналитик требований",
        "терпеливый наставник",
        "senior-разработчик",
        "опытный DevOps-инженер",
        "преподаватель информатики",
        "редактор научных статей",
        "консультант по архитектуре ПО",
        "специалист по информационной безопасности",
        "продуктовый аналитик",
        "тимлид с бэкграундом в ML",
        "архивариус документации",
        "бережливый оптимизатор кода",
    )
    SYSTEM_STYLES: ClassVar[tuple[str, ...]] = (
        "кратко и по делу",
        "подробно, с примерами",
        "пошагово",
        "неформально, простыми словами",
        "со схемами и таблицами в markdown",
        "сначала краткий вывод, затем детали",
        "с аналогиями из повседневной жизни",
        "строго формальным языком",
        "в духе вопрос-ответ, заранее снимая возможные уточнения",
        "энергично, с советами «что попробовать сразу»",
    )
    HUMAN_INTENTS: ClassVar[tuple[str, ...]] = (
        "Объясни, как работает {topic}.",
        "Приведи пример использования {topic}.",
        "Перечисли типичные ошибки при работе с {topic}.",
        "Сравни {topic} с альтернативами.",
        "Какие есть подводные камни у {topic}?",
        "Составь чек-лист по теме «{topic}».",
        "Предложи пошаговый план изучения {topic}.",
        "Реши задачу и объясни ход рассуждений: {topic}.",
        "Напиши мини-реферат на 200 слов о {topic}.",
        "Какие инструменты и библиотеки нужны для работы с {topic}?",
        "Как протестировать решение, связанное с {topic}?",
        "Кратко резюмируй ключевые идеи {topic} в трёх пунктах.",
        "Что произойдёт, если проигнорировать ограничения {topic}?",
        "Подбери метафору, которая объясняет {topic} новичку.",
        "Найди слабые места в типовом описании {topic}.",
    )
    TOPICS: ClassVar[tuple[str, ...]] = (
        "LangChain",
        "LCEL",
        "агенты",
        "RAG",
        "промпт-шаблоны",
        "векторные хранилища",
        "асинхронность в Python",
        "структурированный вывод моделей",
        "оценка качества LLM-приложений",
        "стриминг ответов модели",
        "инструменты и function calling",
        "память и контекст диалога",
        "middleware в агентных пайплайнах",
        "векторные индексы и поиск по сходству",
        "обработка ошибок в цепочках",
        "эффективная токенизация",
        "мультиагентные системы",
        "масштабирование LLM-сервисов",
    )

    __data: ClassVar[
        dict[int, tuple[SystemMessagePromptTemplate, HumanMessagePromptTemplate]]
    ] = {}

    def __init__(self, n_sets: int = 5, seed: int | None = None) -> None:
        """Собирает n_sets случайных наборов промптов в __data."""
        rng = random.Random(seed)
        type(self).__data.clear()
        for i in range(n_sets):
            system = SystemMessagePromptTemplate.from_template(
                f"Ты {rng.choice(self.SYSTEM_ROLES)}. "
                f"Отвечай {rng.choice(self.SYSTEM_STYLES)}."
            )
            human = HumanMessagePromptTemplate.from_template(
                rng.choice(self.HUMAN_INTENTS).format(topic=rng.choice(self.TOPICS))
            )
            type(self).__data[i] = (system, human)

    @staticmethod
    def get_prompt_set() -> tuple[
        SystemMessagePromptTemplate, HumanMessagePromptTemplate
    ]:
        """Возвращает случайный набор промптов из __data."""
        return random.choice(list(TestLLMInfo.__data.values()))

    @staticmethod
    def get_system_prompt() -> SystemMessagePromptTemplate:
        return TestLLMInfo.get_prompt_set()[0]

    @staticmethod
    def get_human_prompt() -> HumanMessagePromptTemplate:
        return TestLLMInfo.get_prompt_set()[1]


@pyinstrument_prof_decorator
@yappi_prof_decor()
def generate_company_chain():

    def displayAIMessage(mesagess: AIMessage):
        match mesagess.content:
            case str() as name_response:
                print(name_response, "\n\n")
            case dict() as name_response:
                for i in dict:
                    print(i)
            case _:
                print("err")

    llm = _create_llm()
    test_data_prompt = TestLLMInfo()

    for _ in range(3):
        prompt = ChatPromptTemplate.from_messages([*test_data_prompt.get_prompt_set()])
        prompt.pretty_print()
        print()
        chain = prompt | llm

        name_response: AIMessage = chain.invoke({})
        displayAIMessage(name_response)


def main():
    generate_company_chain()


if __name__ == "__main__":
    main()
