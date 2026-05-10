import json
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse


class AiSearchApiTests(SimpleTestCase):
    def test_submit_returns_json_when_runtime_unavailable(self):
        with patch(
            'news.views._get_ai_search_runtime_error',
            return_value='服务器未安装 crawl4ai，请执行: pip install -r requirements.txt',
        ):
            response = self.client.post(
                reverse('ai_search_submit'),
                data=json.dumps({
                    'query': 'AI 芯片',
                    'url': 'https://36kr.com',
                    'category': 'tech',
                }),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertIn('crawl_runtime_unavailable', response.json().get('code', ''))

    def test_submit_returns_json_when_task_creation_raises(self):
        with patch('news.views._get_ai_search_runtime_error', return_value=''), patch(
            'news.models.AiSearchTask.objects.create',
            side_effect=RuntimeError('db unavailable'),
        ):
            response = self.client.post(
                reverse('ai_search_submit'),
                data=json.dumps({'query': 'AI 芯片', 'category': 'tech'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        payload = response.json()
        self.assertEqual(payload.get('code'), 'ai_search_submit_failed')
        self.assertIn('AI 搜索服务初始化失败', payload.get('error', ''))

    def test_status_returns_json_when_lookup_raises(self):
        with patch('news.models.AiSearchTask.objects.get', side_effect=RuntimeError('db unavailable')):
            response = self.client.get(reverse('ai_search_status', args=[7]))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        payload = response.json()
        self.assertEqual(payload.get('code'), 'ai_search_status_failed')
        self.assertIn('AI 搜索状态查询失败', payload.get('error', ''))
