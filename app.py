def chatgpt_response(user_message):
    api_key = os.environ.get('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)

    # Google検索クエリを強化
    query = f"宮古島 {user_message}"
    google_info = get_google_search_results(query)

    system_prompt = f"""
あなたはGoogle検索結果を要約する役割です。
以下のGoogle検索結果からのみ情報を抜き出し、他の情報を推測・追加しないでください。

【Google検索結果】
{google_info}

【制約】
- 推測は禁止
- 検索結果がない場合は「現在の情報は見つかりませんでした」と答える
- リンクと簡単な説明を3件まで提示する
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=500,
        temperature=0.2,
    )
    reply_text = response.choices[0].message.content.strip()
    return reply_text
