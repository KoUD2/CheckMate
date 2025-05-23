import re
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def parse_task37_description(task_description: str) -> dict:
    """
    Парсит описание задания 37 и извлекает email, subject и questions_theme.
    
    Args:
        task_description: Полное описание задания 37
        
    Returns:
        dict: Словарь с ключами email, subject, questions_theme
    """
    result = {
        "email": "",
        "subject": "",
        "questions_theme": ""
    }
    
    try:
        # Ищем subject после "Subject: "
        subject_match = re.search(r'Subject:\s*([^\n]+)', task_description)
        if subject_match:
            result["subject"] = subject_match.group(1).strip()
            logger.info(f"Найден subject: {result['subject']}")
        
        # Ищем текст письма между Subject и "Write an email"
        # Паттерн: от строки после Subject до строки с "Write an email"
        email_pattern = r'Subject:[^\n]*\n\n(.*?)\n\nWrite an email'
        email_match = re.search(email_pattern, task_description, re.DOTALL)
        if email_match:
            result["email"] = email_match.group(1).strip()
            logger.info(f"Найден текст письма: {result['email'][:50]}...")
        else:
            # Альтернативный паттерн если нет двойного переноса строки
            email_pattern_alt = r'Subject:[^\n]*\n(.*?)\nWrite an email'
            email_match_alt = re.search(email_pattern_alt, task_description, re.DOTALL)
            if email_match_alt:
                result["email"] = email_match_alt.group(1).strip()
                logger.info(f"Найден текст письма (альт. паттерн): {result['email'][:50]}...")
        
        # Ищем questions_theme после "ask 3 questions about"
        questions_match = re.search(r'ask\s+3\s+questions\s+about\s+([^\n.!?]*)', task_description, re.IGNORECASE)
        if questions_match:
            result["questions_theme"] = questions_match.group(1).strip()
            logger.info(f"Найдена тема вопросов: {result['questions_theme']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге задания 37: {e}")
        return result

def extract_criterion_scores_and_comments(gemini_responses: list, scores: list) -> list:
    """
    Извлекает комментарии по каждому критерию из ответов Gemini.
    
    Args:
        gemini_responses: Список ответов от Gemini для каждого критерия
        scores: Список оценок по критериям [k1, k2, k3]
        
    Returns:
        list: Список словарей с комментариями для каждого критерия
    """
    comments = []
    criterion_names = ["k1", "k2", "k3"]
    
    try:
        for i, (response, score) in enumerate(zip(gemini_responses, scores)):
            comment = {
                "criterion": criterion_names[i],
                "end_pos": 0,
                "start_pos": 0,
                "text": response.strip()
            }
            comments.append(comment)
            logger.info(f"Создан комментарий для критерия {criterion_names[i]}")
        
        return comments
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении комментариев: {e}")
        return [] 