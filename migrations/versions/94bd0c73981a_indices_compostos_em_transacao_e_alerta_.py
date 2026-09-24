"""indices compostos em transacao e alerta, indice em categoria_id

Revision ID: 94bd0c73981a
Revises: 0c68856f9520
Create Date: 2026-09-23 21:04:22.785056

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94bd0c73981a'
down_revision = '0c68856f9520'
branch_labels = None
depends_on = None


# Cria o índice novo antes de derrubar o antigo, pra conta_id nunca ficar sem índice.
# Os compostos (conta_id, data) começam por conta_id, então substituem os
# idx_*_conta_id antigos sem perder nada.
def upgrade():
    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.create_index('idx_transacao_conta_data', ['conta_id', 'data'], unique=False)
        batch_op.create_index('idx_transacao_categoria_id', ['categoria_id'], unique=False)
        batch_op.drop_index(batch_op.f('idx_transacao_conta_id'))

    with op.batch_alter_table('alerta', schema=None) as batch_op:
        batch_op.create_index('idx_alerta_conta_data', ['conta_id', 'data'], unique=False)
        batch_op.drop_index(batch_op.f('idx_alerta_conta_id'))


def downgrade():
    with op.batch_alter_table('alerta', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_alerta_conta_id'), ['conta_id'], unique=False)
        batch_op.drop_index('idx_alerta_conta_data')

    with op.batch_alter_table('transacao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_transacao_conta_id'), ['conta_id'], unique=False)
        batch_op.drop_index('idx_transacao_categoria_id')
        batch_op.drop_index('idx_transacao_conta_data')
