import re
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def parse_task38_description(task_description: str) -> dict:
    """
    Парсит описание задания 38 и извлекает opinion и problem.
    
    Args:
        task_description: Полное описание задания 38
        
    Returns:
        dict: Словарь с ключами opinion, problem
    """
    result = {
        "opinion": "",
        "problem": ""
    }
    
    try:
        # Ищем opinion - то что после "Comment on the survey data and give your opinion on"
        opinion_pattern = r'Comment on the survey data and give your opinion on\s+([^\n.]+)'
        opinion_match = re.search(opinion_pattern, task_description, re.IGNORECASE)
        if opinion_match:
            result["opinion"] = opinion_match.group(1).strip()
            logger.info(f"Найдена тема мнения: {result['opinion']}")
        
        # Ищем problem - то что после "outline a problem that can arise with"
        problem_pattern = r'outline a problem that can arise with\s+([^a-z\n.]+?)(?:\s+and|$)'
        problem_match = re.search(problem_pattern, task_description, re.IGNORECASE)
        if problem_match:
            result["problem"] = problem_match.group(1).strip()
            logger.info(f"Найдена тема проблемы: {result['problem']}")
        else:
            # Fallback паттерн
            problem_pattern_alt = r'outline a problem that can arise with\s+([^\n.]+)'
            problem_match_alt = re.search(problem_pattern_alt, task_description, re.IGNORECASE)
            if problem_match_alt:
                # Обрезаем до "and" если есть
                problem_text = problem_match_alt.group(1).strip()
                if ' and ' in problem_text:
                    problem_text = problem_text.split(' and ')[0].strip()
                result["problem"] = problem_text
                logger.info(f"Найдена тема проблемы (альт. паттерн): {result['problem']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге задания 38: {e}")
        return result

def extract_criterion_scores_and_comments_38(gemini_responses: list, scores: list) -> list:
    """
    Извлекает комментарии по каждому критерию из ответов Gemini для задания 38.
    
    Args:
        gemini_responses: Список ответов от Gemini для каждого критерия (5 критериев)
        scores: Список оценок по критериям [k1, k2, k3, k4, k5]
        
    Returns:
        list: Список словарей с комментариями для каждого критерия
    """
    comments = []
    criterion_names = ["k1", "k2", "k3", "k4", "k5"]
    
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
        logger.error(f"Ошибка при извлечении комментариев для задания 38: {e}")
        return [] 