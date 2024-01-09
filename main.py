import re
import json
import requests
from bs4 import BeautifulSoup
from fake_headers import Headers

def get_text_or_none(element):
    return element.text.strip() if element else None

def replace_nbsp_with_space(data):
    if isinstance(data, str):
        return re.sub(r'\s+', ' ', data.replace('\xa0', ' '))
    elif isinstance(data, list):
        return [replace_nbsp_with_space(item) for item in data]
    elif isinstance(data, dict):
        return {key: replace_nbsp_with_space(value) for key, value in data.items()}
    else:
        return data

def scrape_vacancy_info(vacancy):
    vacancy_name_raw = vacancy.find('span', class_='serp-item__title')
    vacancy_name = get_text_or_none(vacancy_name_raw)

    vacancy_link_raw = vacancy.find('a', class_='bloko-link')
    vacancy_link = vacancy_link_raw['href'] if vacancy_link_raw else None

    vacancy_salary_raw = vacancy.find('span', class_='bloko-header-section-2')
    vacancy_salary = get_text_or_none(vacancy_salary_raw)

    company_name_raw = vacancy.find('a', {'data-qa': 'vacancy-serp__vacancy-employer'})
    company_name = get_text_or_none(company_name_raw)

    vacancy_city_raw = vacancy.find('div', {'data-qa': 'vacancy-serp__vacancy-address'})
    vacancy_city = get_text_or_none(vacancy_city_raw)

    return {
        'name': vacancy_name,
        'link': vacancy_link,
        'salary': vacancy_salary,
        'company': company_name,
        'city': vacancy_city,
        'description': None
    }

def main():
    headers_generator = Headers(os='win', browser='chrome')
    vacancy_info_list = []

    try:
        page_number = 0
        max_pages = 2
        while page_number < max_pages:
            url = f'https://spb.hh.ru/search/vacancy?area=1&area=2&enable_snippets=true&order_by=publication_time&ored_clusters=true&text=python&search_period=1&page={page_number}'
            response = requests.get(url, headers=headers_generator.generate())
            response.raise_for_status()
            html_data = response.text
            soup = BeautifulSoup(html_data, 'lxml')

            vacancy_list = soup.find('div', id='a11y-main-content')
            vacancies = vacancy_list.find_all('div', class_='serp-item')

            for vacancy in vacancies:
                vacancy_info = scrape_vacancy_info(vacancy)

                vacancy_info = replace_nbsp_with_space(vacancy_info)

                response_vacancy = requests.get(vacancy_info['link'], headers=headers_generator.generate())
                vacancy_html_data = response_vacancy.text
                vacancy_soup = BeautifulSoup(vacancy_html_data, 'lxml')

                vacancy_desc_raw = vacancy_soup.find('div', {'data-qa': 'vacancy-description'})
                vacancy_info['description'] = get_text_or_none(vacancy_desc_raw)

                # проверка текста на соответствие условию
                if 'django' in (vacancy_info['description'] or "").lower() or 'flask' in (vacancy_info['description'] or "").lower():
                    vacancy_info_list.append(vacancy_info)

            # Проверка наличия следующей страницы
            next_page_button = soup.find('a', {'data-qa': 'pager-next'})
            if next_page_button:
                page_number += 1
            else:
                break

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    with open('vacancies.json', 'a', encoding='utf-8') as json_file:
        json.dump(vacancy_info_list, json_file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()