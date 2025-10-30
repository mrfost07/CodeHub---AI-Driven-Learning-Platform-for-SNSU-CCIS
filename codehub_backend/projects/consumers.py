import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class ProjectCollaborationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time project collaboration.
    Handles code editor synchronization, cursor positions, and live updates.
    """

    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.project_group_name = f'project_{self.project_id}'
        self.user = self.scope['user']

        # Join project group
        await self.channel_layer.group_add(
            self.project_group_name,
            self.channel_name
        )

        await self.accept()

        # Notify others that user joined
        await self.channel_layer.group_send(
            self.project_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name(),
            }
        )

    async def disconnect(self, close_code):
        # Notify others that user left
        await self.channel_layer.group_send(
            self.project_group_name,
            {
                'type': 'user_left',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name(),
            }
        )

        # Leave project group
        await self.channel_layer.group_discard(
            self.project_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'code_change':
            # Broadcast code changes to all users in the project
            await self.channel_layer.group_send(
                self.project_group_name,
                {
                    'type': 'code_change',
                    'user_id': str(self.user.id),
                    'username': self.user.get_full_name(),
                    'file_path': data.get('file_path'),
                    'changes': data.get('changes'),
                    'timestamp': data.get('timestamp'),
                }
            )

        elif message_type == 'cursor_position':
            # Broadcast cursor position to all users
            await self.channel_layer.group_send(
                self.project_group_name,
                {
                    'type': 'cursor_position',
                    'user_id': str(self.user.id),
                    'username': self.user.get_full_name(),
                    'file_path': data.get('file_path'),
                    'line': data.get('line'),
                    'column': data.get('column'),
                }
            )

        elif message_type == 'task_update':
            # Broadcast task updates
            await self.channel_layer.group_send(
                self.project_group_name,
                {
                    'type': 'task_update',
                    'user_id': str(self.user.id),
                    'username': self.user.get_full_name(),
                    'task_id': data.get('task_id'),
                    'action': data.get('action'),
                    'data': data.get('data'),
                }
            )

        elif message_type == 'file_opened':
            # Notify others about file being opened
            await self.channel_layer.group_send(
                self.project_group_name,
                {
                    'type': 'file_opened',
                    'user_id': str(self.user.id),
                    'username': self.user.get_full_name(),
                    'file_path': data.get('file_path'),
                }
            )

        elif message_type == 'file_closed':
            # Notify others about file being closed
            await self.channel_layer.group_send(
                self.project_group_name,
                {
                    'type': 'file_closed',
                    'user_id': str(self.user.id),
                    'username': self.user.get_full_name(),
                    'file_path': data.get('file_path'),
                }
            )

    # Handler methods for different message types
    async def user_joined(self, event):
        """Send user joined notification"""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'username': event['username'],
        }))

    async def user_left(self, event):
        """Send user left notification"""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'username': event['username'],
        }))

    async def code_change(self, event):
        """Send code change to websocket"""
        # Don't send back to the same user
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'code_change',
                'user_id': event['user_id'],
                'username': event['username'],
                'file_path': event['file_path'],
                'changes': event['changes'],
                'timestamp': event['timestamp'],
            }))

    async def cursor_position(self, event):
        """Send cursor position to websocket"""
        # Don't send back to the same user
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'user_id': event['user_id'],
                'username': event['username'],
                'file_path': event['file_path'],
                'line': event['line'],
                'column': event['column'],
            }))

    async def task_update(self, event):
        """Send task update to websocket"""
        await self.send(text_data=json.dumps({
            'type': 'task_update',
            'user_id': event['user_id'],
            'username': event['username'],
            'task_id': event['task_id'],
            'action': event['action'],
            'data': event['data'],
        }))

    async def file_opened(self, event):
        """Send file opened notification"""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'file_opened',
                'user_id': event['user_id'],
                'username': event['username'],
                'file_path': event['file_path'],
            }))

    async def file_closed(self, event):
        """Send file closed notification"""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'file_closed',
                'user_id': event['user_id'],
                'username': event['username'],
                'file_path': event['file_path'],
            }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """

    async def connect(self):
        self.user = self.scope['user']
        
        if self.user.is_authenticated:
            self.notification_group_name = f'notifications_{self.user.id}'

            # Join notification group
            await self.channel_layer.group_add(
                self.notification_group_name,
                self.channel_name
            )

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            # Leave notification group
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Receive message from WebSocket (for acknowledgments, etc.)
        """
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'mark_read':
            notification_id = data.get('notification_id')
            # Handle marking notification as read
            # This would typically update the database
            pass

    async def notification(self, event):
        """Send notification to websocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
        }))

    async def notification_count(self, event):
        """Send unread notification count"""
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': event['count'],
        }))

