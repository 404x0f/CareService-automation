"""add dialog models

Revision ID: 20261011_dialog_models
Revises: c0c364b8c9f6
Create Date: 2026-10-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = '20261011_dialog_models'
down_revision: Union[str, None] = 'c0c364b8c9f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chats',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('avito_chat_id', sa.String(length=255), nullable=False),
        sa.Column('avito_user_id', sa.String(length=255), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'answered',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
        sa.Column('waiting_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('avito_chat_id', name='uq_chats_avito_chat_id'),
    )
    op.create_table(
        'messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('avito_message_id', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'sent_by_manager',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('avito_message_id', name='uq_messages_avito_message_id'),
    )
    op.create_table(
        'reply_reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('chat_id', sa.Uuid(), nullable=False),
        sa.Column('suggested_reply', sa.Text(), nullable=False),
        sa.Column('final_reply', sa.Text(), nullable=True),
        sa.Column(
            'state',
            sa.String(length=32),
            server_default='pending',
            nullable=False,
        ),
        sa.Column('manager_id', sa.Uuid(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('reply_reviews')
    op.drop_table('messages')
    op.drop_table('chats')
