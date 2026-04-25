import re


class ExtractContent:
    def endOfBracketFinder(self, main_string, bracket=("[", "]"), string_char='"'):
        no_of_brackets_open = 1
        open_bracket = bracket[0]
        close_bracket = bracket[1]
        string_lock = False
        for x in range(1, len(main_string)):
            if main_string[x] == string_char and main_string[x - 1] != "\\":
                string_lock = not string_lock
            if not string_lock:
                if main_string[x] == open_bracket:
                    no_of_brackets_open += 1
                elif main_string[x] == close_bracket:
                    no_of_brackets_open -= 1
                if no_of_brackets_open == 0:
                    return x
        return -1


    def extract_edges(self, dict_keys, text=None, json_dict=None):
        return self.nested_dict_extractor_without_key_error(json_dict, dict_keys=dict_keys)

    def extract_profile_id(self, text):
        page_ids = re.findall(r'"query":{"content_type":"PROFILE","target_id":"(.*?)"}', text)

        return list(set(page_ids))[0]

    def nested_dict_extractor_without_key_error(self, json_obj, dict_keys):
        temp_dict = json_obj
        for key in dict_keys:
            temp_dict = temp_dict.get(key, {}) or {}
        return temp_dict


    def extract_instagram_profile_json(self, response):
        try:
            data = response.json()
        except ValueError:
            return {}

        user = data.get('data', {}).get('user') or {}

        def clean_bio(bio):
            if not bio:
                return ""

            cleaned = ' '.join(
                line.strip() for line in bio.split('\n') if line.strip()
            )
            return cleaned

        profile = {
            'username': user.get('username', ''),
            'fullname': user.get('full_name', '').split('|')[0].strip(),
            # 'fullname': user.get('full_name', ''),
            'bio': clean_bio(user.get('biography', '')),
            'followers': user.get('follower_count', 0),
            'following': user.get('following_count', 0),
            'media_count': user.get('media_count', 0),
            'profile_pic': user.get('hd_profile_pic_url_info', {}).get('url', ''),
            'account_type': user.get('account_type', ''),
            'category': user.get('category', '')
        }
        print(f"the profile details is : {profile}")

        return profile